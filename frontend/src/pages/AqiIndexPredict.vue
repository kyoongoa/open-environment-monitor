<template>
  <section class="predict-page">
    <header class="predict-page__head">
      <h2>AQI指数预测</h2>
    </header>

    <div class="predict-page__body">
      <div class="predict-page__card predict-page__form-card">
        <div class="predict-page__form">
          <input v-model.trim="form.city" type="text" placeholder="城市" />
          <select v-model="form.season">
            <option value="" disabled>请选择季节</option>
            <option value="春季">春季</option>
            <option value="夏季">夏季</option>
            <option value="秋季">秋季</option>
            <option value="冬季">冬季</option>
          </select>
          <input v-model.number="form.pm25" type="number" step="0.1" placeholder="PM2.5" />
          <input v-model.number="form.pm10" type="number" step="0.1" placeholder="PM10" />
          <input v-model.number="form.so2" type="number" step="0.1" placeholder="SO2" />
          <input v-model.number="form.no2" type="number" step="0.1" placeholder="NO2" />
          <input v-model.number="form.co" type="number" step="0.1" placeholder="CO" />
          <input v-model.number="form.o3" type="number" step="0.1" placeholder="O3" />
        </div>
        <div class="predict-page__actions">
          <button type="button" class="secondary" @click="fillExample">填充示例数据</button>
          <button type="button" class="ghost" @click="resetForm">清空</button>
          <button type="button" @click="predict">预测</button>
        </div>
      </div>

      <div class="predict-page__card predict-page__result">
        <div class="predict-page__result-label">AQI指数</div>
        <div class="predict-page__result-value">{{ resultDisplay }}</div>
      </div>

      <div class="predict-page__card predict-page__shap" v-if="result !== null">
        <div class="predict-page__shap-head">
          <h3>SHAP 贡献解释</h3>
          <span v-if="shapBaseValue !== null">基线值：{{ shapBaseValue }}</span>
        </div>

        <p v-if="shapError" class="predict-page__shap-error">{{ shapError }}</p>

        <div v-else class="predict-page__shap-list">
          <div v-for="item in shapTopItems" :key="item.feature" class="predict-page__shap-item">
            <div class="predict-page__shap-meta">
              <strong>{{ item.feature }}</strong>
              <span :class="{ up: item.shap_value > 0, down: item.shap_value < 0 }">
                {{ item.shap_value > 0 ? "+" : "" }}{{ item.shap_value }}（{{ item.direction }}）
              </span>
            </div>
            <div class="predict-page__shap-bar">
              <i
                :class="{ up: item.shap_value > 0, down: item.shap_value < 0 }"
                :style="{ width: `${Math.min(100, Math.abs(item.shap_value) * 12)}%` }"
              ></i>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import axios from "axios";
import { computed, reactive, ref } from "vue";

const API_BASE_URL = "/api/auth";

const form = reactive({
  city: "",
  season: "",
  pm25: null,
  pm10: null,
  so2: null,
  no2: null,
  co: null,
  o3: null,
});

const result = ref(null);
const resultDisplay = computed(() => (result.value === null ? "-" : String(result.value)));
const shapItems = ref([]);
const shapBaseValue = ref(null);
const shapError = ref("");
const shapTopItems = computed(() => shapItems.value.slice(0, 8));

function fillExample() {
  form.city = "北京";
  form.season = "春季";
  form.pm25 = 35;
  form.pm10 = 55;
  form.so2 = 10;
  form.no2 = 22;
  form.co = 0.8;
  form.o3 = 75;
}

function resetForm() {
  form.city = "";
  form.season = "";
  form.pm25 = null;
  form.pm10 = null;
  form.so2 = null;
  form.no2 = null;
  form.co = null;
  form.o3 = null;
  result.value = null;
  shapItems.value = [];
  shapBaseValue.value = null;
  shapError.value = "";
}

async function predict() {
  if (!form.city || !form.season) {
    return;
  }

  const { data } = await axios.post(`${API_BASE_URL}/aqi-index-predict/`, {
    city: form.city,
    season: form.season,
    pm25: form.pm25,
    pm10: form.pm10,
    so2: form.so2,
    no2: form.no2,
    co: form.co,
    o3: form.o3,
  });
  result.value = data.aqi_index;

  const shap = data.shap || {};
  if (shap.available) {
    shapItems.value = Array.isArray(shap.items) ? shap.items : [];
    shapBaseValue.value = shap.base_value ?? null;
    shapError.value = "";
  } else {
    shapItems.value = [];
    shapBaseValue.value = null;
    shapError.value = shap.message || "暂无SHAP解释";
  }
}
</script>

<style scoped>
.predict-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.predict-page__head h2 {
  margin: 0;
  font-size: 30px;
  color: #16343d;
}

.predict-page__body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.predict-page__card {
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(198, 214, 221, 0.9);
  box-shadow: 0 10px 30px rgba(22, 52, 61, 0.08);
}

.predict-page__form-card {
  padding: 14px;
}

.predict-page__form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.predict-page__form input,
.predict-page__form select,
.predict-page__actions button {
  min-height: 38px;
  border: 1px solid #cad7de;
  border-radius: 10px;
  padding: 0 12px;
  font-weight: 600;
}

.predict-page__form input {
  min-height: 40px;
  border: 1px solid #c7d4db;
  border-radius: 10px;
  padding: 0 10px;
  background: #fff;
}

.predict-page__actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 12px;
}

.predict-page__actions button {
  color: #fff;
  background: #1f7f74;
  border-color: #1f7f74;
  cursor: pointer;
}

.predict-page__actions button.secondary {
  background: #4d94b8;
  border-color: #4d94b8;
}

.predict-page__actions button.ghost {
  color: #1f7f74;
  background: #fff;
  border-color: #9fb7c3;
}

.predict-page__result {
  padding: 24px 18px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 14px;
}

.predict-page__result-label {
  font-size: 22px;
  color: #355a67;
}

.predict-page__result-value {
  min-width: 190px;
  min-height: 190px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 35% 30%, #f8fdff, #dfeef4);
  border: 1px solid #c3d6df;
  font-size: 68px;
  line-height: 1;
  font-weight: 700;
  color: #16343d;
}

.predict-page__shap {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.predict-page__shap-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.predict-page__shap-head h3 {
  margin: 0;
  font-size: 18px;
  color: #214755;
}

.predict-page__shap-head span {
  font-size: 13px;
  color: #5b7583;
}

.predict-page__shap-error {
  margin: 0;
  color: #8f3a31;
  background: #fff2ef;
  border: 1px solid #f1c9c3;
  border-radius: 8px;
  padding: 8px 10px;
}

.predict-page__shap-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.predict-page__shap-item {
  padding: 8px 10px;
  border-radius: 10px;
  background: #f7fbff;
  border: 1px solid #e0ebf3;
}

.predict-page__shap-meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}

.predict-page__shap-meta strong {
  color: #274b5a;
}

.predict-page__shap-meta span {
  font-size: 12px;
}

.predict-page__shap-meta span.up {
  color: #b44b41;
}

.predict-page__shap-meta span.down {
  color: #2f7e5b;
}

.predict-page__shap-bar {
  margin-top: 6px;
  height: 6px;
  background: #e7edf2;
  border-radius: 999px;
  overflow: hidden;
}

.predict-page__shap-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
}

.predict-page__shap-bar i.up {
  background: #d96b61;
}

.predict-page__shap-bar i.down {
  background: #4aa578;
}

@media (max-width: 1100px) {
  .predict-page__form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .predict-page__form {
    grid-template-columns: 1fr;
  }

  .predict-page__actions {
    flex-direction: column;
  }
}
</style>

