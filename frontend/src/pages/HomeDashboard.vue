<template>
  <section class="dashboard-home">
    <template v-if="isAdminPortal">
      <header class="dashboard-home__title">
        <h2>管理工作台</h2>
        <p>系统概览与常用管理入口。</p>
      </header>

      <section class="admin-cards">
        <article class="admin-card">
          <p>天气数据总量</p>
          <strong>{{ adminSummary.weatherTotal }}</strong>
          <span>条记录</span>
        </article>
        <article class="admin-card">
          <p>空气质量数据总量</p>
          <strong>{{ adminSummary.airTotal }}</strong>
          <span>条记录</span>
        </article>
        <article class="admin-card">
          <p>今日日期</p>
          <strong>{{ adminSummary.today }}</strong>
          <span>系统时间</span>
        </article>
        <article class="admin-card">
          <p>数据状态</p>
          <strong>{{ adminSummary.status }}</strong>
          <span>{{ adminSummary.statusDetail }}</span>
        </article>
      </section>

      <section class="quick-entry">
        <h3>快捷入口</h3>
        <div class="quick-entry__grid">
          <button type="button" @click="goQuick('weather-manage')">天气数据管理</button>
          <button type="button" @click="goQuick('air-manage')">空气质量数据管理</button>
          <button type="button" @click="goQuick('profile')">个人中心</button>
          <button type="button" @click="fetchAdminSummary">刷新概览</button>
        </div>
      </section>
    </template>

    <template v-else>
      <header class="dashboard-home__title">
        <h2>首页实时天气仪表盘</h2>
        <p>输入任意城市名称，查看由已配置数据提供者返回的最新环境观测。</p>
      </header>

      <section class="live-board">
      <header class="live-board__top">
        <div class="live-board__filters">
          <label>城市 <input v-model="selectedCity" placeholder="例如：北京" @keyup.enter="fetchLiveData" /></label>
        </div>
        <div class="live-board__meta">
          <strong>{{ currentCityName }}</strong>
          <span>{{ formattedTime }} 更新</span>
        </div>
        <button type="button" :disabled="loading" @click="fetchLiveData">刷新</button>
      </header>

      <div class="live-board__panel">
        <section class="gauge-panel">
          <div ref="gaugeRef" class="gauge-panel__chart"></div>
          <div class="gauge-panel__text">
            <p>空气质量等级</p>
          <strong>{{ liveData?.quality || "-" }}</strong>
          <span>{{ liveData?.aqi ?? "-" }} US AQI（按 PM2.5 计算）</span>
          </div>
        </section>

        <section class="metric-panel">
          <article v-for="item in metricItems" :key="item.key" class="metric-row">
            <div class="metric-row__head">
              <span>{{ item.label }}</span>
              <strong>{{ item.value }} <small>{{ item.unit }}</small></strong>
            </div>
            <div class="metric-row__bar">
              <i :style="{ width: `${item.percent}%`, background: item.color }"></i>
            </div>
          </article>
        </section>
      </div>
      <footer class="live-board__tips">
        <span>数据源：{{ liveData?.source || "—" }}</span>
        <span>状态：{{ liveData?.data_status || "unavailable" }}</span>
      </footer>

      <section class="trend-card">
        <div class="trend-card__head">
          <h3>当日小时趋势</h3>
          <span>城市：{{ currentCityName }}</span>
        </div>
        <div ref="trendRef" class="trend-card__chart"></div>
      </section>

      <section class="days-list-card">
        <div class="days-list-card__head">
          <h3>近几日天气数据列表</h3>
          <span>按日聚合（最近时段）</span>
        </div>
        <div class="days-list-card__table-wrap">
          <table class="days-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>AQI</th>
                <th>等级</th>
                <th>首要污染物</th>
                <th>PM2.5_24h</th>
                <th>PM10_24h</th>
                <th>O3_8h_24h</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="recentDays.length === 0">
                <td colspan="7" class="days-table__empty">暂无近几日数据</td>
              </tr>
              <tr v-for="row in recentDays" :key="row.time_point || row.date_label">
                <td>{{ row.observed_at || "-" }}</td>
                <td>{{ row.aqi ?? "-" }}</td>
                <td>{{ row.quality || "-" }}</td>
                <td>—</td>
                <td>{{ row.pm25 ?? "-" }}</td>
                <td>{{ row.pm10 ?? "-" }}</td>
                <td>{{ row.o3 ?? "-" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <p v-if="errorMsg" class="live-board__error">{{ errorMsg }}</p>
      </section>
    </template>
  </section>
</template>

<script setup>
import axios from "axios";
import * as echarts from "echarts";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const API_BASE_URL = "/api/auth";
const ENVIRONMENT_API_URL = "/api/environment";
const props = defineProps({
  isAdminPortal: {
    type: Boolean,
    default: false,
  },
  onQuickNav: {
    type: Function,
    default: null,
  },
});

const loading = ref(false);
const errorMsg = ref("");
const selectedCity = ref("北京");
const liveData = ref(null);
const trendRows = ref([]);
const recentDays = ref([]);
const adminSummary = ref({
  weatherTotal: 0,
  airTotal: 0,
  today: "-",
  status: "加载中",
  statusDetail: "正在读取真实观测",
});

const gaugeRef = ref(null);
const trendRef = ref(null);
let gaugeInstance = null;
let trendInstance = null;
let timer = null;

const pollutantConfig = [
  { key: "pm25", label: "PM2.5", unit: "μg/m³", max: 250, color: "#45b2ff" },
  { key: "pm10", label: "PM10", unit: "μg/m³", max: 300, color: "#6ed59b" },
  { key: "so2", label: "SO2", unit: "μg/m³", max: 800, color: "#f8b15a" },
  { key: "no2", label: "NO2", unit: "μg/m³", max: 400, color: "#f07c9f" },
  { key: "co", label: "CO", unit: "μg/m³", max: 20000, color: "#9a88ff" },
  { key: "o3", label: "O3", unit: "μg/m³", max: 300, color: "#48d1c5" },
];

const currentCityName = computed(() => liveData.value?.city || selectedCity.value || "-");

const formattedTime = computed(() => {
  const raw = liveData.value?.observed_at || liveData.value?.cache_stored_at;
  if (!raw) return "-";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString("zh-CN", { hour12: false });
});

const metricItems = computed(() => {
  const data = liveData.value || {};
  return pollutantConfig.map((item) => {
    const val = Number(data[item.key] ?? 0);
    const percent = Math.min(100, Math.max(0, (val / item.max) * 100));
    return {
      key: item.key,
      label: item.label,
      unit: item.unit,
      value: Number.isFinite(val) ? val : "-",
      percent,
      color: item.color,
    };
  });
});

function renderGauge() {
  if (!gaugeRef.value) return;
  if (!gaugeInstance) {
    gaugeInstance = echarts.init(gaugeRef.value);
  }
  const value = Number(liveData.value?.aqi ?? 0);
  const safeValue = Number.isFinite(value) ? value : 0;
  gaugeInstance.setOption(
    {
      series: [
        {
          type: "gauge",
          min: 0,
          max: 300,
          splitNumber: 6,
          axisLine: {
            roundCap: true,
            lineStyle: {
              width: 18,
              color: [
                [0.17, "#67c23a"],
                [0.33, "#e6a23c"],
                [0.5, "#f56c6c"],
                [0.67, "#d24dff"],
                [0.83, "#8f5fff"],
                [1, "#6f3f9c"],
              ],
            },
          },
          pointer: { show: false },
          progress: {
            show: true,
            width: 18,
            roundCap: true,
            itemStyle: { color: "#ffffff" },
          },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          detail: {
            valueAnimation: true,
            formatter: "{value}",
            color: "#1f425a",
            fontSize: 42,
            offsetCenter: [0, "12%"],
          },
          title: {
            offsetCenter: [0, "-34%"],
            color: "#5f7788",
            fontSize: 16,
          },
          data: [{ value: safeValue, name: "AQI指数" }],
        },
      ],
    },
    true,
  );
}

function renderTrend() {
  if (!trendRef.value) return;
  if (!trendInstance) {
    trendInstance = echarts.init(trendRef.value);
  }

  const rows = trendRows.value || [];
  const xAxisData = rows.map((item) => item.observed_at || "");
  const aqi = rows.map((item) => item.aqi);
  const pm25 = rows.map((item) => item.pm25);
  const pm10 = rows.map((item) => item.pm10);

  trendInstance.setOption(
    {
      animationDuration: 900,
      tooltip: { trigger: "axis" },
      legend: {
        top: 0,
        icon: "roundRect",
        itemWidth: 12,
        itemHeight: 8,
        textStyle: { color: "#4d6576" },
      },
      grid: { left: 36, right: 18, top: 34, bottom: 24, containLabel: true },
      xAxis: {
        type: "category",
        data: xAxisData,
        axisLabel: { color: "#6b8291", fontSize: 11 },
        axisLine: { lineStyle: { color: "#d7e3ec" } },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#6b8291" },
        splitLine: { lineStyle: { color: "#edf3f7" } },
      },
      series: [
        {
          name: "AQI",
          type: "line",
          smooth: true,
          showSymbol: false,
          data: aqi,
          lineStyle: { width: 2, color: "#4d94b8" },
          areaStyle: { color: "rgba(77,148,184,0.10)" },
        },
        {
          name: "PM2.5",
          type: "line",
          smooth: true,
          showSymbol: false,
          data: pm25,
          lineStyle: { width: 2, color: "#66b88f" },
        },
        {
          name: "PM10",
          type: "line",
          smooth: true,
          showSymbol: false,
          data: pm10,
          lineStyle: { width: 2, color: "#e2a757" },
        },
      ],
    },
    true,
  );
}

async function fetchLiveData() {
  loading.value = true;
  errorMsg.value = "";
  try {
    const { data } = await axios.get(`${ENVIRONMENT_API_URL}/realtime/`, { params: { city: selectedCity.value } });
    liveData.value = data.data || null;
    const historyResponse = await axios.get(`${ENVIRONMENT_API_URL}/trend/`, { params: { city: selectedCity.value } });
    trendRows.value = historyResponse.data.data || [];
    recentDays.value = trendRows.value.slice(-14).reverse();
    await nextTick();
    renderGauge();
    renderTrend();
  } catch (error) {
    errorMsg.value = error?.response?.data?.error?.message || "实时数据加载失败";
  } finally {
    loading.value = false;
  }
}

async function fetchAdminSummary() {
  try {
    const { data } = await axios.get(`${ENVIRONMENT_API_URL}/dashboard-summary/`);
    const summary = data.data || {};
    adminSummary.value = {
      weatherTotal: summary.weather_observations || 0,
      airTotal: summary.air_quality_observations || 0,
      today: new Date().toLocaleDateString("zh-CN"),
      status: summary.status_label || "暂无数据",
      statusDetail: summary.status_detail || "尚无成功获取的真实环境观测",
    };
  } catch (error) {
    adminSummary.value = {
      ...adminSummary.value,
      today: new Date().toLocaleDateString("zh-CN"),
      status: "异常",
      statusDetail: "工作台统计接口不可用",
    };
  }
}

function goQuick(key) {
  if (props.onQuickNav) {
    props.onQuickNav(key);
  }
}

function resizeGauge() {
  if (gaugeInstance) gaugeInstance.resize();
  if (trendInstance) trendInstance.resize();
}

onMounted(async () => {
  if (props.isAdminPortal) {
    await fetchAdminSummary();
  } else {
    await fetchLiveData();
    timer = setInterval(fetchLiveData, 5 * 60 * 1000);
  }
  window.addEventListener("resize", resizeGauge);
});

watch(selectedCity, (newCity, oldCity) => {
  if (props.isAdminPortal) return;
  if (!newCity || newCity === oldCity) return;
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  window.removeEventListener("resize", resizeGauge);
  if (gaugeInstance) {
    gaugeInstance.dispose();
    gaugeInstance = null;
  }
  if (trendInstance) {
    trendInstance.dispose();
    trendInstance = null;
  }
});
</script>

<style scoped>
.dashboard-home {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.admin-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.admin-card {
  border: 1px solid #dbe7ef;
  background: #fff;
  border-radius: 14px;
  padding: 14px;
  box-shadow: 0 4px 12px rgba(24, 58, 84, 0.05);
}

.admin-card p {
  margin: 0;
  color: #6c8291;
  font-size: 13px;
}

.admin-card strong {
  display: block;
  margin-top: 6px;
  font-size: 28px;
  color: #1f4560;
}

.admin-card span {
  color: #7c93a2;
  font-size: 12px;
}

.quick-entry {
  border: 1px solid #dbe7ef;
  background: #fff;
  border-radius: 14px;
  padding: 18px;
}

.quick-entry h3 {
  margin: 0 0 14px;
  color: #274a60;
  font-size: 18px;
}

.quick-entry__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.quick-entry__grid button {
  min-height: 74px;
  border: 1px solid #c8dce8;
  border-radius: 12px;
  background: linear-gradient(180deg, #f8fcff, #edf5fb);
  color: #2a566e;
  cursor: pointer;
  font-weight: 600;
  font-size: 16px;
  box-shadow: 0 6px 14px rgba(30, 70, 96, 0.08);
}

.quick-entry__grid button:hover {
  background: linear-gradient(180deg, #f1f8fd, #e7f2fa);
  transform: translateY(-1px);
}

.dashboard-home__title h2 {
  margin: 0 0 6px;
  font-size: 28px;
  font-weight: 700;
  color: #19394e;
}

.dashboard-home__title p {
  margin: 0;
  color: #667f90;
}

.live-board {
  background: #ffffff;
  border-radius: 16px;
  padding: 14px;
  color: #1f3b48;
  box-shadow: 0 4px 14px rgba(24, 58, 84, 0.06);
  border: 1px solid #e0e8ef;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.live-board__top {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: end;
  gap: 14px;
  background: #f5f9fc;
  border: 1px solid #e3edf5;
  border-radius: 12px;
  padding: 12px;
}

.live-board__filters {
  display: flex;
  gap: 10px;
}

.live-board__filters label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #3f5d72;
  font-weight: 600;
}

.live-board__filters select {
  min-width: 180px;
  min-height: 36px;
  border: 1px solid #c7d7e4;
  border-radius: 8px;
  padding: 0 10px;
  color: #2b4b62;
  background: #ffffff;
}

.live-board__meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.live-board__meta strong {
  font-size: 34px;
  line-height: 1;
  color: #1f4560;
}

.live-board__meta span {
  font-size: 14px;
  color: #6b8291;
}

.live-board__top button {
  min-height: 36px;
  border: 1px solid #b9cddd;
  border-radius: 8px;
  padding: 0 14px;
  color: #2d4f67;
  background: #ffffff;
  font-weight: 600;
  cursor: pointer;
}

.live-board__panel {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
}

.gauge-panel {
  border-radius: 12px;
  background: #f8fbfe;
  border: 1px solid #e0eaf2;
  padding: 8px 8px 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #2b4e65;
}

.gauge-panel__chart {
  width: 100%;
  height: 230px;
}

.gauge-panel__text {
  text-align: center;
}

.gauge-panel__text p {
  margin: 0;
  font-size: 13px;
  color: #5f7788;
}

.gauge-panel__text strong {
  display: block;
  margin-top: 4px;
  font-size: 24px;
  color: #2b4e65;
}

.gauge-panel__text span {
  font-size: 14px;
  color: #6d8392;
}

.metric-panel {
  border-radius: 12px;
  background: #f8fbfe;
  border: 1px solid #e0eaf2;
  padding: 12px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
}

.metric-row {
  background: #ffffff;
  border: 1px solid #e5edf4;
  border-radius: 10px;
  padding: 10px;
}

.metric-row__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.metric-row__head span {
  font-size: 17px;
  color: #2a4c61;
}

.metric-row__head strong {
  font-size: 24px;
  font-weight: 800;
  color: #2d4f64;
}

.metric-row__head small {
  font-size: 13px;
  font-weight: 500;
  opacity: 0.65;
}

.metric-row__bar {
  margin-top: 8px;
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: #e5edf5;
  overflow: hidden;
}

.metric-row__bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
}

.live-board__tips {
  border-radius: 10px;
  background: #f8fbfe;
  border: 1px solid #e0eaf2;
  padding: 10px 12px;
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #345567;
  animation: fadeSlideUp 0.45s ease both;
}

.trend-card {
  border-radius: 12px;
  background: #f8fbfe;
  border: 1px solid #e0eaf2;
  padding: 10px 12px;
  animation: fadeSlideUp 0.55s ease both;
}

.trend-card__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 6px;
}

.trend-card__head h3 {
  margin: 0;
  font-size: 16px;
  color: #25465c;
}

.trend-card__head span {
  color: #6b8291;
  font-size: 13px;
}

.trend-card__chart {
  height: 280px;
}

.live-board__error {
  margin-top: 10px;
  background: #fff1ef;
  color: #8c2f27;
  border: 1px solid #f0c9c3;
  border-radius: 8px;
  padding: 8px 10px;
}

.days-list-card {
  border-radius: 12px;
  background: #f8fbfe;
  border: 1px solid #e0eaf2;
  padding: 10px 12px;
  animation: fadeSlideUp 0.65s ease both;
}

.days-list-card__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 8px;
}

.days-list-card__head h3 {
  margin: 0;
  font-size: 16px;
  color: #25465c;
}

.days-list-card__head span {
  color: #6b8291;
  font-size: 13px;
}

.days-list-card__table-wrap {
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid #e4edf4;
  background: #ffffff;
}

.days-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}

.days-table th,
.days-table td {
  padding: 9px 10px;
  border-bottom: 1px solid #edf2f6;
  text-align: left;
  color: #395668;
  font-size: 13px;
  white-space: nowrap;
}

.days-table th {
  background: #f6f9fc;
  color: #5e7889;
  font-weight: 700;
}

.days-table__empty {
  text-align: center !important;
  color: #7b919f !important;
}

@keyframes fadeSlideUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1200px) {
  .admin-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .quick-entry__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .live-board__top {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .live-board__meta {
    align-items: flex-start;
  }

  .live-board__panel {
    grid-template-columns: 1fr;
  }

  .gauge-panel__chart {
    height: 260px;
  }
}

@media (max-width: 760px) {
  .admin-cards {
    grid-template-columns: 1fr;
  }

  .quick-entry__grid {
    grid-template-columns: 1fr;
  }

  .live-board__filters {
    flex-direction: row;
  }

  .metric-panel {
    grid-template-columns: 1fr;
  }

  .live-board__tips {
    flex-direction: column;
    gap: 8px;
  }

  .trend-card__head {
    flex-direction: column;
    align-items: flex-start;
  }

  .trend-card__chart {
    height: 240px;
  }

  .days-list-card__head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>

