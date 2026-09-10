<template>
  <section class="data-page">
    <header class="data-page__head"><h2>天气观测数据</h2><p>只读展示由 Provider 获取并持久化的真实天气观测。</p></header>
    <div class="filters">
      <input v-model.trim="filters.city" placeholder="城市" />
      <input v-model="filters.start_date" type="date" />
      <input v-model="filters.end_date" type="date" />
      <button @click="search">筛选</button><button class="secondary" @click="resetFilters">重置</button>
    </div>
    <div class="data-page__table-wrap"><table class="data-table"><thead><tr><th>观测时间</th><th>城市</th><th>温度 °C</th><th>湿度 %</th><th>天气</th><th>风速 m/s</th><th>来源</th><th>采集时间</th></tr></thead><tbody>
      <tr v-if="loading"><td colspan="8" class="state-cell">加载中...</td></tr><tr v-else-if="errorMsg"><td colspan="8" class="state-cell">{{ errorMsg }}</td></tr><tr v-else-if="!rows.length"><td colspan="8" class="state-cell">暂无真实天气观测</td></tr>
      <tr v-for="row in rows" :key="row.id"><td>{{ formatTime(row.observed_at) }}</td><td>{{ row.city }}</td><td>{{ row.temperature ?? "-" }}</td><td>{{ row.humidity ?? "-" }}</td><td>{{ row.weather || "-" }}</td><td>{{ row.wind_speed ?? "-" }}</td><td>{{ row.source }}</td><td>{{ formatTime(row.collected_at) }}</td></tr>
    </tbody></table></div>
    <footer class="pager"><span>共 {{ total }} 条</span><button :disabled="page <= 1 || loading" @click="goPage(page - 1)">上一页</button><span>第 {{ page }} / {{ totalPages }} 页</span><button :disabled="page >= totalPages || loading" @click="goPage(page + 1)">下一页</button></footer>
  </section>
</template>
<script setup>
import axios from "axios"; import { onMounted, reactive, ref } from "vue";
const rows = ref([]), total = ref(0), page = ref(1), totalPages = ref(1), loading = ref(false), errorMsg = ref("");
const filters = reactive({ city: "", start_date: "", end_date: "" });
const formatTime = (value) => value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-";
async function fetchData() { loading.value = true; errorMsg.value = ""; try { const { data } = await axios.get("/api/environment/weather-observations/", { params: { page: page.value, page_size: 20, city: filters.city || undefined, start_date: filters.start_date || undefined, end_date: filters.end_date || undefined } }); rows.value = data.results || []; total.value = data.total || 0; page.value = data.page || 1; totalPages.value = data.total_pages || 1; } catch (error) { errorMsg.value = error?.response?.data?.error?.message || "天气观测加载失败"; } finally { loading.value = false; } }
function search() { page.value = 1; fetchData(); } function resetFilters() { Object.assign(filters, { city: "", start_date: "", end_date: "" }); search(); } function goPage(value) { page.value = value; fetchData(); } onMounted(fetchData);
</script>
<style scoped>
.data-page { display:flex; flex-direction:column; gap:18px; min-height:100%; }.data-page__head h2 { margin:0 0 8px; color:#16343d; }.data-page__head p,.state-cell { color:#56717d; }.filters { display:flex; flex-wrap:wrap; align-items:center; gap:12px; padding:16px; border:1px solid #d9e6ed; border-radius:12px; background:rgba(255,255,255,.88); }.filters input,.filters button,.pager button { box-sizing:border-box; height:42px; min-height:42px; padding:0 12px; border:1px solid #c8d8e1; border-radius:8px; background:#fff; }.filters input:first-child { width:200px; }.filters input[type="date"] { width:180px; }.filters button { min-width:76px; background:#2c6f8d; color:#fff; cursor:pointer; }.filters .secondary { background:#f3f8fb; color:#35586d; }.data-page__table-wrap { overflow-x:auto; background:rgba(255,255,255,.8); border-radius:12px; border:1px solid #d9e6ed; }.data-table { width:100%; min-width:960px; border-collapse:collapse; }.data-table th,.data-table td { padding:10px 12px; border-bottom:1px solid #e2eaee; text-align:left; white-space:nowrap; }.data-table th { background:#f4f8fa; }.state-cell { text-align:center !important; }.pager { display:flex; flex-wrap:wrap; align-items:center; gap:12px; padding:12px 16px; border:1px solid #d9e6ed; border-radius:12px; background:rgba(255,255,255,.88); }.pager button { cursor:pointer; } .pager button:disabled { opacity:.5; } @media (max-width:720px) { .filters { align-items:stretch; } .filters input,.filters input:first-child,.filters input[type="date"],.filters button { width:100%; } }
</style>
