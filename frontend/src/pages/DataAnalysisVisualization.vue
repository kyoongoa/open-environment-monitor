<template>
  <section class="analysis-page">
    <div v-if="loading" class="analysis-page__state">正在加载图表数据...</div>
    <div v-else-if="errorMsg" class="analysis-page__state analysis-page__state--error">{{ errorMsg }}</div>

    <section
      v-for="analysis in visibleAnalyses"
      :key="analysis.key"
      class="analysis-section"
      :id="analysis.key"
    >
      <h3 class="analysis-section__title">{{ analysis.title }}</h3>
      <div class="analysis-grid">
        <article v-for="chart in analysis.charts" :key="chart.key" class="chart-card">
          <h4 class="chart-card__title">{{ chart.title }}</h4>
          <div :ref="(el) => setChartRef(chart.table, el)" class="chart-card__plot"></div>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup>
import axios from "axios";
import * as echarts from "echarts";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  activeNav: {
    type: String,
    default: "analysis_city_diff",
  },
});

const API_BASE_URL = "/api/auth";
const analyses = ref([]);
const loading = ref(false);
const errorMsg = ref("");
const chartRefs = new Map();
const chartInstances = new Map();
let renderRound = 0;
const CHART_COLORS = [
  "#4d94b8",
  "#d09e54",
  "#d65d53",
  "#7b8fcb",
  "#7da87b",
  "#3f6f99",
  "#b57ea8",
  "#5f6773",
  "#3da5a8",
  "#c07a3b",
];

const analysisNavMap = {
  analysis_city_diff: "analysis_city_diff",
  analysis_time_series: "analysis_time_series",
  analysis_season_cycle: "analysis_season_cycle",
  analysis_weather_impact: "analysis_weather_impact",
  analysis_pollutant_relation: "analysis_pollutant_relation",
};

const visibleAnalyses = computed(() => {
  const analysisKey = analysisNavMap[props.activeNav];
  if (!analysisKey) {
    return analyses.value;
  }
  return analyses.value.filter((item) => item.key === analysisKey);
});

function setChartRef(table, el) {
  if (el) {
    chartRefs.set(table, el);
  } else {
    chartRefs.delete(table);
    const instance = chartInstances.get(table);
    if (instance) {
      instance.dispose();
      chartInstances.delete(table);
    }
  }
}

function splitName(name) {
  const text = String(name ?? "");
  return text.split("|");
}

function pickColor(seedText, offset = 0) {
  let hash = 0;
  const text = String(seedText || "");
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
  }
  return CHART_COLORS[(hash + offset) % CHART_COLORS.length];
}

function buildSimpleOption(rows, type, yName = "值", color = "#4d94b8") {
  const xAxisData = rows.map((r) => r.name);
  const seriesData = rows.map((r) => Number(r.value ?? 0));
  return {
    tooltip: { trigger: type === "line" ? "axis" : "item" },
    grid: { left: 40, right: 20, top: 24, bottom: 36, containLabel: true },
    xAxis: {
      type: "category",
      data: xAxisData,
      axisLabel: { rotate: xAxisData.length > 12 ? 30 : 0, color: "#56717d" },
    },
    yAxis: { type: "value", name: yName, axisLabel: { color: "#56717d" } },
    series: [
      {
        type,
        data: seriesData,
        smooth: type === "line",
        itemStyle: { color },
        lineStyle: { color, width: 2 },
        areaStyle: type === "line" ? { color: `${color}33` } : undefined,
      },
    ],
  };
}

function withEntranceAnimation(option, chartKey = "") {
  const baseDelay = (String(chartKey).length * 37 + renderRound * 53) % 280;
  const series = (option.series || []).map((s) => ({
    ...s,
    animation: true,
    animationDuration: s.type === "line" ? 1200 : 900,
    animationEasing: "cubicOut",
    animationDelay: (idx) => baseDelay + Math.min(idx * 45, 360),
    animationDurationUpdate: 500,
    animationEasingUpdate: "cubicInOut",
  }));

  return {
    ...option,
    animation: true,
    animationThreshold: 3000,
    animationDuration: 1000,
    animationEasing: "cubicOut",
    animationDurationUpdate: 500,
    animationEasingUpdate: "cubicInOut",
    series,
  };
}

function buildMultiSeriesOption(rows, yName = "值") {
  const grouped = new Map();
  const xSet = new Set();

  for (const row of rows) {
    const [seriesName, xName] = splitName(row.name);
    if (!grouped.has(seriesName)) {
      grouped.set(seriesName, new Map());
    }
    grouped.get(seriesName).set(xName, Number(row.value ?? 0));
    xSet.add(xName);
  }

  const xAxisData = Array.from(xSet).sort();
  const palette = CHART_COLORS;
  const series = Array.from(grouped.entries()).map(([seriesName, dataMap], index) => ({
    name: seriesName,
    type: "line",
    smooth: true,
    showSymbol: false,
    data: xAxisData.map((x) => dataMap.get(x) ?? null),
    lineStyle: { width: 2, color: palette[index % palette.length] },
    itemStyle: { color: palette[index % palette.length] },
  }));

  return {
    tooltip: { trigger: "axis" },
    legend: { top: 0, type: "scroll" },
    grid: { left: 40, right: 18, top: 36, bottom: 32, containLabel: true },
    xAxis: {
      type: "category",
      data: xAxisData,
      axisLabel: { rotate: xAxisData.length > 18 ? 40 : 0, color: "#56717d" },
    },
    yAxis: { type: "value", name: yName, axisLabel: { color: "#56717d" } },
    series,
  };
}

function buildAreaMultiSeriesOption(rows, yName = "值") {
  const option = buildMultiSeriesOption(rows, yName);
  option.series = (option.series || []).map((s) => ({
    ...s,
    areaStyle: { color: `${s.itemStyle?.color || "#4d94b8"}22` },
    stack: "total",
  }));
  return option;
}

function buildStackBarOption(rows, yName = "占比(%)") {
  const citySet = new Set();
  const levelSet = new Set();
  const matrix = new Map();

  for (const row of rows) {
    const [city, level] = splitName(row.name);
    citySet.add(city);
    levelSet.add(level);
    matrix.set(`${city}|${level}`, Number(row.value ?? 0));
  }

  const cities = Array.from(citySet);
  const levels = Array.from(levelSet);
  const palette = CHART_COLORS;
  const series = levels.map((level, index) => ({
    name: level,
    type: "bar",
    stack: "total",
    itemStyle: { color: palette[index % palette.length] },
    data: cities.map((city) => matrix.get(`${city}|${level}`) ?? 0),
  }));

  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { top: 0, type: "scroll" },
    grid: { left: 40, right: 16, top: 36, bottom: 30, containLabel: true },
    xAxis: { type: "category", data: cities },
    yAxis: { type: "value", name: yName },
    series,
  };
}

function buildHorizontalBarOption(rows, yName = "值") {
  const sorted = [...rows].sort((a, b) => Number(b.value ?? 0) - Number(a.value ?? 0));
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { left: 70, right: 18, top: 18, bottom: 16, containLabel: true },
    xAxis: { type: "value", name: yName, axisLabel: { color: "#56717d" } },
    yAxis: { type: "category", data: sorted.map((r) => r.name), axisLabel: { color: "#56717d" } },
    series: [
      {
        type: "bar",
        data: sorted.map((r, i) => ({
          value: Number(r.value ?? 0),
          itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
        })),
      },
    ],
  };
}

function buildBarLineYoYOption(rows, yName = "占比(%)") {
  const sorted = [...rows].sort((a, b) => String(a.name).localeCompare(String(b.name)));
  const years = sorted.map((r) => r.name);
  const ratio = sorted.map((r) => Number(r.value ?? 0));
  const yoy = ratio.map((v, i) => (i === 0 ? null : Number((v - ratio[i - 1]).toFixed(2))));

  return {
    tooltip: { trigger: "axis" },
    legend: { top: 0, data: ["优良天占比", "同比变化"] },
    grid: { left: 44, right: 40, top: 34, bottom: 26, containLabel: true },
    xAxis: { type: "category", data: years, axisLabel: { color: "#56717d" } },
    yAxis: [
      { type: "value", name: yName, axisLabel: { color: "#56717d" } },
      { type: "value", name: "同比(%)", axisLabel: { color: "#56717d" } },
    ],
    series: [
      {
        name: "优良天占比",
        type: "bar",
        data: ratio,
        barMaxWidth: 26,
        itemStyle: { color: "#4d94b8" },
      },
      {
        name: "同比变化",
        type: "line",
        yAxisIndex: 1,
        data: yoy,
        smooth: true,
        showSymbol: true,
        symbolSize: 7,
        lineStyle: { color: "#d09e54", width: 2 },
        itemStyle: { color: "#d09e54" },
      },
    ],
  };
}

function buildPieOption(rows) {
  const data = rows.map((r, i) => ({
    name: r.name,
    value: Number(r.value ?? 0),
    itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
  }));
  return {
    tooltip: { trigger: "item" },
    legend: { bottom: 0, type: "scroll" },
    series: [
      {
        type: "pie",
        radius: ["45%", "72%"],
        center: ["50%", "45%"],
        label: { formatter: "{b}" },
        data,
      },
    ],
  };
}

function buildRadarOption(rows, valueName = "值") {
  const values = rows.map((r) => Number(r.value ?? 0));
  const maxValue = Math.max(...values, 1) * 1.2;
  return {
    tooltip: {},
    radar: {
      radius: "64%",
      indicator: rows.map((r) => ({ name: r.name, max: maxValue })),
      axisName: { color: "#4f6474", fontSize: 11 },
      splitArea: { areaStyle: { color: ["#f7fbff", "#f2f8fd"] } },
      splitLine: { lineStyle: { color: "#dbe7f0" } },
    },
    series: [
      {
        type: "radar",
        name: valueName,
        data: [{ value: values }],
        areaStyle: { color: "rgba(77,148,184,0.26)" },
        lineStyle: { color: "#4d94b8", width: 2 },
        itemStyle: { color: "#4d94b8" },
      },
    ],
  };
}

function buildHeatmapFromPair(rows) {
  const xSet = new Set();
  const ySet = new Set();
  const matrix = [];
  for (const row of rows) {
    const [xName, yName] = splitName(row.name);
    xSet.add(xName);
    ySet.add(yName);
  }
  const xAxisData = Array.from(xSet);
  const yAxisData = Array.from(ySet);
  const xIndex = new Map(xAxisData.map((name, idx) => [name, idx]));
  const yIndex = new Map(yAxisData.map((name, idx) => [name, idx]));
  for (const row of rows) {
    const [xName, yName] = splitName(row.name);
    matrix.push([xIndex.get(xName), yIndex.get(yName), Number(row.value ?? 0)]);
  }
  const vals = matrix.map((x) => x[2]);
  const vmax = vals.length ? Math.max(...vals) : 1;
  return {
    tooltip: { position: "top" },
    grid: { left: 56, right: 20, top: 20, bottom: 30, containLabel: true },
    xAxis: { type: "category", data: xAxisData, splitArea: { show: true } },
    yAxis: { type: "category", data: yAxisData, splitArea: { show: true } },
    visualMap: {
      min: 0,
      max: vmax,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: { color: ["#eef6fb", "#4d94b8"] },
    },
    series: [{ type: "heatmap", data: matrix }],
  };
}

function buildScatterOption(rows, xName, yName, color = "#7b8fcb") {
  const data = rows.map((row) => [Number(row.name), Number(row.value ?? 0)]).filter((item) => Number.isFinite(item[0]));
  return {
    tooltip: {
      trigger: "item",
      formatter: (params) => `${xName}: ${params.value[0]}<br/>${yName}: ${params.value[1]}`,
    },
    grid: { left: 42, right: 18, top: 20, bottom: 34, containLabel: true },
    xAxis: { type: "value", name: xName },
    yAxis: { type: "value", name: yName },
    series: [
      {
        type: "scatter",
        data,
        symbolSize: 6,
        itemStyle: { color: `${color}aa` },
      },
    ],
  };
}

function buildBubbleScatterOption(rows, xName, yName, color = "#7b8fcb") {
  const data = rows
    .map((row) => [Number(row.name), Number(row.value ?? 0)])
    .filter((item) => Number.isFinite(item[0]) && Number.isFinite(item[1]));
  const yMax = data.length ? Math.max(...data.map((d) => d[1])) : 1;
  return {
    tooltip: {
      trigger: "item",
      formatter: (params) => `${xName}: ${params.value[0]}<br/>${yName}: ${params.value[1]}`,
    },
    grid: { left: 42, right: 18, top: 20, bottom: 34, containLabel: true },
    xAxis: { type: "value", name: xName },
    yAxis: { type: "value", name: yName },
    series: [
      {
        type: "scatter",
        data,
        symbolSize: (val) => {
          const ratio = yMax > 0 ? val[1] / yMax : 0;
          return 6 + ratio * 20;
        },
        itemStyle: { color: `${color}99` },
      },
    ],
  };
}

function buildHeatmapOption(rows) {
  const xSet = new Set();
  const ySet = new Set();
  const matrix = [];

  for (const row of rows) {
    const [xName, yName] = splitName(row.name);
    xSet.add(xName);
    ySet.add(yName);
  }

  const xAxisData = Array.from(xSet);
  const yAxisData = Array.from(ySet);
  const xIndex = new Map(xAxisData.map((name, idx) => [name, idx]));
  const yIndex = new Map(yAxisData.map((name, idx) => [name, idx]));

  for (const row of rows) {
    const [xName, yName] = splitName(row.name);
    matrix.push([xIndex.get(xName), yIndex.get(yName), Number(row.value ?? 0)]);
  }

  return {
    tooltip: { position: "top" },
    grid: { left: 44, right: 20, top: 20, bottom: 28, containLabel: true },
    xAxis: { type: "category", data: xAxisData, splitArea: { show: true } },
    yAxis: { type: "category", data: yAxisData, splitArea: { show: true } },
    visualMap: {
      min: -1,
      max: 1,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: { color: ["#d65d53", "#f1f4f6", "#1f7f74"] },
    },
    series: [{ type: "heatmap", data: matrix, label: { show: false } }],
  };
}

function createOption(chart) {
  const rows = chart.rows || [];
  const baseColor = pickColor(chart.table);
  switch (chart.table) {
    case "part1":
      return buildSimpleOption(rows, "bar", "AQI", baseColor);
    case "part2":
      return buildPieOption(rows);
    case "part3":
      return buildStackBarOption(rows, "占比(%)");
    case "part4":
      return buildRadarOption(rows, "污染天数");
    case "part5":
      return buildAreaMultiSeriesOption(rows, "PM2.5");
    case "part6":
      return buildMultiSeriesOption(rows, "AQI");
    case "part7":
      return buildAreaMultiSeriesOption(rows, "PM2.5");
    case "part8":
      return buildSimpleOption(rows, "bar", "AQI", baseColor);
    case "part9":
      return buildScatterOption(rows, "年份", "PM2.5", pickColor(chart.table, 3));
    case "part10":
      return buildBarLineYoYOption(rows, "优良率(%)");
    case "part11":
      return buildSimpleOption(rows, "line", "AQI", baseColor);
    case "part12":
      return buildSimpleOption(rows, "line", "PM2.5", baseColor);
    case "part13":
      return buildSimpleOption(rows, "bar", "AQI", baseColor);
    case "part14":
      return buildPieOption(rows);
    case "part15":
      return buildHeatmapFromPair(rows);
    case "part16":
      return buildHorizontalBarOption(rows, "PM2.5");
    case "part17":
      return buildPieOption(rows);
    case "part18":
      return buildRadarOption(rows, "PM2.5");
    case "part19":
      return buildSimpleOption(rows, "bar", "PM2.5", baseColor);
    case "part20":
      return buildScatterOption(rows, "温度(℃)", "PM2.5", pickColor(chart.table, 1));
    case "part21":
      return buildAreaMultiSeriesOption(rows, "浓度");
    case "part23":
      return buildScatterOption(rows, "PM2.5", "PM10", pickColor(chart.table, 2));
    case "part24":
      return buildBubbleScatterOption(rows, "PM2.5", "NO2", pickColor(chart.table, 3));
    case "part25":
      return buildSimpleOption(rows, "bar", "O3", pickColor(chart.table, 4));
    case "part22":
      return buildHeatmapOption(rows);
    default:
      if (chart.type === "line_multi") {
        return buildMultiSeriesOption(rows);
      }
      if (chart.type === "line") {
        return buildSimpleOption(rows, "line", "值", baseColor);
      }
      return buildSimpleOption(rows, "bar", "值", baseColor);
  }
}

function createOptionWithAnimation(chart) {
  const option = createOption(chart);
  if (option?.series) {
    return withEntranceAnimation(option, chart.table);
  }
  return option;
}

function renderCharts() {
  renderRound += 1;
  for (const analysis of visibleAnalyses.value) {
    for (const chart of analysis.charts) {
      const el = chartRefs.get(chart.table);
      if (!el) continue;

      let instance = chartInstances.get(chart.table);
      if (instance && instance.getDom() !== el) {
        instance.dispose();
        chartInstances.delete(chart.table);
        instance = null;
      }
      if (!instance) {
        instance = echarts.init(el);
        chartInstances.set(chart.table, instance);
      }
      instance.setOption(createOptionWithAnimation(chart), true);
    }
  }
}

async function fetchAnalysisData() {
  loading.value = true;
  errorMsg.value = "";
  try {
    const { data } = await axios.get(`${API_BASE_URL}/analysis-visualization/`);
    analyses.value = data.analyses || [];
    await nextTick();
    renderCharts();
  } catch (error) {
    errorMsg.value = error?.response?.data?.message || "分析图表数据加载失败";
  } finally {
    loading.value = false;
  }
}

function handleResize() {
  for (const instance of chartInstances.values()) {
    instance.resize();
  }
}

watch(
  () => props.activeNav,
  async () => {
    await nextTick();
    renderCharts();
    handleResize();
  },
);

onMounted(() => {
  fetchAnalysisData();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  for (const instance of chartInstances.values()) {
    instance.dispose();
  }
  chartInstances.clear();
});
</script>

<style scoped>
.analysis-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 100%;
  height: calc(100vh - 54px);
}

.analysis-page__state {
  padding: 18px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.68);
  color: #56717d;
}

.analysis-page__state--error {
  color: #b94f46;
}

.analysis-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 100%;
  flex: 1;
}

.analysis-section__title {
  margin: 0;
  font-size: 20px;
  color: #1b4149;
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(3, minmax(0, 1fr));
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.chart-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-radius: 14px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(200, 214, 222, 0.76);
  min-height: 0;
  opacity: 0;
  transform: translateY(14px);
  animation: chartCardIn 0.55s ease forwards;
}

.chart-card__title {
  margin: 0;
  font-size: 13px;
  color: #345964;
  line-height: 1.35;
}

.analysis-grid .chart-card:nth-child(1) {
  animation-delay: 0.04s;
}

.analysis-grid .chart-card:nth-child(2) {
  animation-delay: 0.09s;
}

.analysis-grid .chart-card:nth-child(3) {
  animation-delay: 0.14s;
}

.analysis-grid .chart-card:nth-child(4) {
  animation-delay: 0.19s;
}

.analysis-grid .chart-card:nth-child(5) {
  animation-delay: 0.24s;
}

@keyframes chartCardIn {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chart-card__plot {
  height: 100%;
  width: 100%;
  min-height: 220px;
}

.analysis-grid .chart-card:nth-child(5) {
  grid-column: 1 / -1;
}

.analysis-grid .chart-card:nth-child(5) .chart-card__plot {
  min-height: 260px;
}

@media (max-width: 1500px) {
  .analysis-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1050px) {
  .analysis-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .analysis-page {
    height: auto;
  }

  .analysis-section {
    min-height: auto;
  }

  .analysis-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    flex: none;
  }

  .analysis-grid .chart-card:nth-child(5) {
    grid-column: auto;
  }

  .analysis-grid .chart-card:nth-child(5) .chart-card__plot {
    height: 260px;
  }
}
</style>

