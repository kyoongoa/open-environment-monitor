<template>
  <section class="data-page">
    <header class="data-page__head">
      <h2>{{ isAdminPortal ? "空气质量数据管理" : "空气质量数据浏览" }}</h2>
      <p>{{ isAdminPortal ? "支持筛选、分页、新增、编辑与删除。" : "支持筛选与分页浏览。" }}</p>
    </header>

    <div class="toolbar">
      <div class="filters">
        <input v-model.trim="filters.city" type="text" placeholder="城市" />
        <input v-model.trim="filters.quality_level" type="text" placeholder="质量等级" />
        <input v-model.number="filters.min_aqi" type="number" placeholder="最小AQI" />
        <input v-model.number="filters.max_aqi" type="number" placeholder="最大AQI" />
        <input v-model="filters.start_date" type="date" />
        <input v-model="filters.end_date" type="date" />
        <button type="button" @click="search">筛选</button>
        <button type="button" class="secondary" @click="resetFilters">重置</button>
      </div>
      <button v-if="isAdminPortal" class="add-btn" type="button" @click="openCreate">新增空气质量数据</button>
    </div>

    <div class="data-page__table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>日期</th>
            <th>城市</th>
            <th>质量等级</th>
            <th>AQI</th>
            <th>排名</th>
            <th>PM2.5</th>
            <th>PM10</th>
            <th>SO2</th>
            <th>NO2</th>
            <th>CO</th>
            <th>O3</th>
            <th v-if="isAdminPortal">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td :colspan="isAdminPortal ? 12 : 11" class="state-cell">加载中...</td>
          </tr>
          <tr v-else-if="errorMsg">
            <td :colspan="isAdminPortal ? 12 : 11" class="state-cell">{{ errorMsg }}</td>
          </tr>
          <tr v-else-if="rows.length === 0">
            <td :colspan="isAdminPortal ? 12 : 11" class="state-cell">暂无数据</td>
          </tr>
          <tr v-else v-for="row in rows" :key="row.id">
            <td>{{ row.record_date || "-" }}</td>
            <td>{{ row.city || "-" }}</td>
            <td>{{ row.quality_level || "-" }}</td>
            <td>{{ row.aqi_index ?? "-" }}</td>
            <td>{{ row.aqi_rank ?? "-" }}</td>
            <td>{{ row.pm25 ?? "-" }}</td>
            <td>{{ row.pm10 ?? "-" }}</td>
            <td>{{ row.so2 ?? "-" }}</td>
            <td>{{ row.no2 ?? "-" }}</td>
            <td>{{ row.co ?? "-" }}</td>
            <td>{{ row.o3 ?? "-" }}</td>
            <td v-if="isAdminPortal" class="ops">
              <button type="button" class="op-btn" @click="openEdit(row)">编辑</button>
              <button type="button" class="op-btn danger" @click="removeRow(row.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="data-page__pager">
      <span>共 {{ total }} 条</span>
      <label>
        每页
        <select v-model.number="pageSize" @change="changePageSize">
          <option :value="20">20</option>
          <option :value="50">50</option>
          <option :value="100">100</option>
        </select>
        条
      </label>
      <button type="button" :disabled="page <= 1 || loading" @click="goPage(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页</span>
      <button type="button" :disabled="page >= totalPages || loading" @click="goPage(page + 1)">下一页</button>
    </footer>

    <div v-if="isAdminPortal && editor.visible" class="modal-mask" @click.self="closeEditor">
      <section class="modal-card">
        <h3>{{ editor.isEdit ? "编辑空气质量数据" : "新增空气质量数据" }}</h3>
        <div class="form-grid">
          <label>日期<input v-model="editor.form.record_date" type="date" /></label>
          <label>城市<input v-model.trim="editor.form.city" type="text" /></label>
          <label>质量等级<input v-model.trim="editor.form.quality_level" type="text" /></label>
          <label>AQI<input v-model.number="editor.form.aqi_index" type="number" /></label>
          <label>排名<input v-model.number="editor.form.aqi_rank" type="number" /></label>
          <label>PM2.5<input v-model.number="editor.form.pm25" type="number" step="0.01" /></label>
          <label>PM10<input v-model.number="editor.form.pm10" type="number" step="0.01" /></label>
          <label>SO2<input v-model.number="editor.form.so2" type="number" step="0.01" /></label>
          <label>NO2<input v-model.number="editor.form.no2" type="number" step="0.01" /></label>
          <label>CO<input v-model.number="editor.form.co" type="number" step="0.01" /></label>
          <label>O3<input v-model.number="editor.form.o3" type="number" step="0.01" /></label>
        </div>
        <div class="modal-actions">
          <button type="button" class="secondary" @click="closeEditor">取消</button>
          <button type="button" @click="saveEditor">保存</button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import axios from "axios";
import { onMounted, reactive, ref } from "vue";

const API_BASE_URL = "/api/auth";
defineProps({
  isAdminPortal: {
    type: Boolean,
    default: false,
  },
});

const rows = ref([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const totalPages = ref(1);
const loading = ref(false);
const errorMsg = ref("");

const filters = reactive({
  city: "",
  quality_level: "",
  min_aqi: null,
  max_aqi: null,
  start_date: "",
  end_date: "",
});

const editor = reactive({
  visible: false,
  isEdit: false,
  form: {
    id: null,
    record_date: "",
    city: "",
    quality_level: "",
    aqi_index: null,
    aqi_rank: null,
    pm25: null,
    pm10: null,
    so2: null,
    no2: null,
    co: null,
    o3: null,
  },
});

async function fetchData() {
  loading.value = true;
  errorMsg.value = "";
  try {
    const { data } = await axios.get(`${API_BASE_URL}/air-quality-data/`, {
      params: {
        page: page.value,
        page_size: pageSize.value,
        city: filters.city || undefined,
        quality_level: filters.quality_level || undefined,
        min_aqi: Number.isFinite(filters.min_aqi) ? filters.min_aqi : undefined,
        max_aqi: Number.isFinite(filters.max_aqi) ? filters.max_aqi : undefined,
        start_date: filters.start_date || undefined,
        end_date: filters.end_date || undefined,
      },
    });
    rows.value = data.results || [];
    total.value = data.total || 0;
    page.value = data.page || 1;
    totalPages.value = data.total_pages || 1;
  } catch (error) {
    errorMsg.value = error?.response?.data?.message || "空气质量数据加载失败";
  } finally {
    loading.value = false;
  }
}

function search() {
  page.value = 1;
  fetchData();
}

function resetFilters() {
  filters.city = "";
  filters.quality_level = "";
  filters.min_aqi = null;
  filters.max_aqi = null;
  filters.start_date = "";
  filters.end_date = "";
  search();
}

function goPage(targetPage) {
  page.value = targetPage;
  fetchData();
}

function changePageSize() {
  page.value = 1;
  fetchData();
}

function openCreate() {
  editor.visible = true;
  editor.isEdit = false;
  Object.assign(editor.form, {
    id: null,
    record_date: "",
    city: "",
    quality_level: "",
    aqi_index: null,
    aqi_rank: null,
    pm25: null,
    pm10: null,
    so2: null,
    no2: null,
    co: null,
    o3: null,
  });
}

function openEdit(row) {
  editor.visible = true;
  editor.isEdit = true;
  Object.assign(editor.form, {
    id: row.id,
    record_date: row.record_date || "",
    city: row.city || "",
    quality_level: row.quality_level || "",
    aqi_index: row.aqi_index,
    aqi_rank: row.aqi_rank,
    pm25: row.pm25,
    pm10: row.pm10,
    so2: row.so2,
    no2: row.no2,
    co: row.co,
    o3: row.o3,
  });
}

function closeEditor() {
  editor.visible = false;
}

async function saveEditor() {
  const payload = { ...editor.form };
  try {
    if (editor.isEdit) {
      await axios.put(`${API_BASE_URL}/air-quality-data/`, payload);
    } else {
      await axios.post(`${API_BASE_URL}/air-quality-data/`, payload);
    }
    closeEditor();
    fetchData();
  } catch (error) {
    alert(error?.response?.data?.message || "保存失败");
  }
}

async function removeRow(id) {
  if (!confirm("确认删除该记录？")) {
    return;
  }
  try {
    await axios.delete(`${API_BASE_URL}/air-quality-data/`, { params: { id } });
    fetchData();
  } catch (error) {
    alert(error?.response?.data?.message || "删除失败");
  }
}

onMounted(fetchData);
</script>

<style scoped>
.data-page { display: flex; flex-direction: column; gap: 16px; min-height: 100%; }
.data-page__head h2 { margin: 0 0 8px; font-size: 28px; color: #16343d; }
.data-page__head p { margin: 0; color: #56717d; }
.toolbar { display: flex; gap: 10px; align-items: stretch; }
.filters {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 10px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #d9e6ed;
}
.filters input {
  min-height: 38px;
  padding: 0 12px;
  border: 1px solid #c8d8e1;
  border-radius: 10px;
  background: #fff;
  outline: none;
}
.filters input:focus {
  border-color: #6f99b3;
  box-shadow: 0 0 0 3px rgba(111, 153, 179, 0.14);
}
.filters button {
  min-height: 38px;
  border-radius: 10px;
  border: 1px solid #2c6f8d;
  background: linear-gradient(120deg, #2c6f8d, #3d86a8);
  color: #fff;
  cursor: pointer;
  font-weight: 600;
}
.filters button:hover { filter: brightness(1.04); }
.filters button.secondary {
  border-color: #c7d6e0;
  background: #f3f8fb;
  color: #35586d;
}
.add-btn {
  min-width: 170px;
  border-radius: 12px;
  border: 1px solid #2f7596;
  background: linear-gradient(120deg, #2f7596, #3f8bb0);
  color: #fff;
  cursor: pointer;
  font-weight: 600;
  box-shadow: 0 8px 16px rgba(47, 117, 150, 0.2);
}
.add-btn:hover { transform: translateY(-1px); }
.data-page__table-wrap { overflow: auto; border-radius: 16px; background: rgba(255, 255, 255, 0.8); }
.data-table { width: 100%; border-collapse: collapse; min-width: 1240px; }
.data-table th, .data-table td { padding: 10px 12px; border-bottom: 1px solid #e2eaee; text-align: left; white-space: nowrap; }
.data-table thead th { font-weight: 600; color: #244753; background: #f4f8fa; }
.state-cell { text-align: center !important; color: #6f8792; }
.ops { display: flex; gap: 6px; }
.op-btn {
  min-height: 30px;
  padding: 0 10px;
  border-radius: 8px;
  background: #357a9a;
  border: 1px solid #357a9a;
  color: #fff;
  cursor: pointer;
}
.op-btn:hover { filter: brightness(1.05); }
.op-btn.danger { background: #c94f4f; border-color: #c94f4f; }
.data-page__pager {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid #d9e6ed;
}
.data-page__pager button,
.data-page__pager select {
  min-height: 34px;
  border-radius: 8px;
  border: 1px solid #c7d6e0;
  background: #fff;
  padding: 0 10px;
}
.data-page__pager button {
  color: #2f5f77;
  cursor: pointer;
}
.modal-mask { position: fixed; inset: 0; z-index: 80; background: rgba(10, 26, 38, 0.38); display: flex; align-items: center; justify-content: center; padding: 20px; }
.modal-card { width: min(980px, 100%); background: #fff; border-radius: 14px; padding: 16px; box-shadow: 0 20px 48px rgba(17, 45, 60, 0.3); }
.modal-card h3 { margin: 0 0 12px; }
.form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.form-grid label { display: flex; flex-direction: column; gap: 6px; color: #3b5c6f; font-size: 13px; }
.form-grid input { min-height: 36px; }
.modal-actions { margin-top: 14px; display: flex; justify-content: flex-end; gap: 8px; }
.modal-actions button {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid #2c6f8d;
  background: linear-gradient(120deg, #2c6f8d, #3d86a8);
  color: #fff;
  cursor: pointer;
}
.modal-actions .secondary {
  border-color: #c7d6e0;
  background: #f3f8fb;
  color: #35586d;
}
@media (max-width: 1300px) { .toolbar { flex-direction: column; } .filters { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 980px) { .form-grid { grid-template-columns: 1fr; } }
</style>

