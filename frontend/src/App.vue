<template>
  <div class="app-shell">
    <div v-if="!isAuthenticated" class="bg-layer" :style="{ backgroundImage: `url(${backgroundImage})` }"></div>
    <div v-if="!isAuthenticated" class="bg-overlay"></div>

    <div v-if="!isAuthenticated" class="deco-ring deco-ring-1"></div>
    <div v-if="!isAuthenticated" class="deco-ring deco-ring-2"></div>
    <div v-if="!isAuthenticated" class="deco-dot deco-dot-1"></div>
    <div v-if="!isAuthenticated" class="deco-dot deco-dot-2"></div>
    <div v-if="!isAuthenticated" class="scan-line"></div>
    <div v-if="!isAuthenticated" class="particles">
      <div
        v-for="particle in particles"
        :key="particle.id"
        class="particle"
        :style="particle.style"
      ></div>
    </div>

    <div v-if="!isAuthenticated" class="ticker">
      <div class="ticker-item">
        <div class="ticker-dot" style="background:#1f7f74"></div>
        <span class="ticker-label">AQI</span>
        <span class="ticker-value">{{ ticker.aqi }}</span>
      </div>
      <div class="ticker-item">
        <div class="ticker-dot" style="background:#4d94b8"></div>
        <span class="ticker-label">PM2.5</span>
        <span class="ticker-value">{{ ticker.pm25 }} μg</span>
      </div>
      <div class="ticker-item">
        <div class="ticker-dot" style="background:#d09e54"></div>
        <span class="ticker-label">TEMP</span>
        <span class="ticker-value">{{ ticker.temp }}°C</span>
      </div>
    </div>

    <div class="toast" :class="{ show: toast.show }" :style="{ background: toast.background }">
      {{ toast.message }}
    </div>

    <main v-if="!isAuthenticated" class="page">
      <div class="card">
        <header class="card-hero">
          <div class="site-logo">
            <div class="logo-icon">
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
                <path
                  d="M5.64 5.64l2.12 2.12M16.24 16.24l2.12 2.12M5.64 18.36l2.12-2.12M16.24 7.76l2.12-2.12"
                />
              </svg>
            </div>
            <div class="hero-text">
              <h1 class="site-title">环境监测数据分析系统</h1>
            </div>
          </div>
        </header>

        <div class="tabs" :data-active="activeTab" :class="{ 'tabs--single': loginPortal === 'admin' }">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'login' }"
            @click="switchTab('login')"
          >
            登 录
          </button>
          <button
            v-if="loginPortal === 'user'"
            class="tab-btn"
            :class="{ active: activeTab === 'register' }"
            @click="switchTab('register')"
          >
            注 册
          </button>
          <div v-if="loginPortal === 'user'" class="tab-indicator"></div>
        </div>

        <div class="forms-wrap">
          <div class="form-panel" id="login-form" :class="{ hidden: activeTab !== 'login' }">
            <div class="input-group">
              <label class="input-label">账 号</label>
              <div class="input-wrap">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <input
                  v-model="loginForm.username"
                  type="text"
                  :placeholder="loginPortal === 'admin' ? '请输入管理员账号' : '请输入用户名或邮箱'"
                  autocomplete="username"
                />
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">密 码</label>
              <div class="input-wrap">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0110 0v4" />
                </svg>
                <input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  autocomplete="current-password"
                />
              </div>
            </div>

            <div class="portal-switch portal-switch--inline">
              <button
                class="portal-switch__btn"
                :class="{ active: loginPortal === 'user' }"
                type="button"
                @click="switchPortal('user')"
              >
                用户端
              </button>
              <button
                class="portal-switch__btn"
                :class="{ active: loginPortal === 'admin' }"
                type="button"
                @click="switchPortal('admin')"
              >
                管理端
              </button>
            </div>

            <div class="row-extra">
              <label class="checkbox-label">
                <input v-model="loginForm.remember" type="checkbox" />
                <span class="custom-check">
                  <svg viewBox="0 0 12 12" fill="none">
                    <polyline points="2,6 5,9 10,3" />
                  </svg>
                </span>
                记住我
              </label>
              <a href="#" class="forgot-link" @click.prevent="showToast('请联系管理员重置密码', false)">忘记密码？</a>
            </div>

            <button class="btn-submit" @click="handleLogin">
              <span class="btn-shine"></span>
              {{ loginPortal === "admin" ? "管理员登录" : "登录系统" }}
            </button>
          </div>

          <div
            v-if="loginPortal === 'user'"
            class="form-panel"
            id="register-form"
            :class="{ hidden: activeTab !== 'register' }"
          >
            <div class="input-group">
              <label class="input-label">用户名</label>
              <div class="input-wrap">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <input v-model="registerForm.username" type="text" placeholder="请输入用户名（4-20位）" />
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">电子邮箱</label>
              <div class="input-wrap">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path
                    d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"
                  />
                  <polyline points="22,6 12,13 2,6" />
                </svg>
                <input v-model="registerForm.email" type="email" placeholder="请输入常用邮箱地址" />
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">登录密码</label>
              <div class="input-wrap">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0110 0v4" />
                </svg>
                <input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="至少8位，含字母+数字"
                  @input="checkStrength"
                />
              </div>
              <div class="strength-wrap" :style="{ display: registerForm.password.length ? 'block' : 'none' }">
                <div class="strength-bar">
                  <div class="strength-fill" :style="strengthStyle"></div>
                </div>
                <div class="strength-text" :style="{ color: strengthStyle.background }">{{ strengthText }}</div>
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">确认密码</label>
              <div class="input-wrap">
                <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                <input v-model="registerForm.confirmPassword" type="password" placeholder="再次输入密码" />
              </div>
            </div>

            <button class="btn-submit" @click="handleRegister">
              <span class="btn-shine"></span>
              创建账户
            </button>

            <p class="agree-text">
              注册即表示您同意我们的
              <a href="#" @click.prevent>《用户服务协议》</a>
              和
              <a href="#" @click.prevent>《隐私政策》</a>
            </p>
          </div>
        </div>
      </div>

      <footer class="site-footer">
        © 2025 Environmental Monitoring System &nbsp;·&nbsp; Powered by EcoSense AI
      </footer>
    </main>

    <div v-else class="workspace-shell">
      <button
        v-if="isAdminIdentity"
        class="portal-jump-btn"
        type="button"
        @click="togglePortalMode"
      >
        {{ loginPortal === "admin" ? "返回前台" : "进入后台" }}
      </button>
      <AppSidebarLayout
        :active-key="activeNav"
        :items="sidebarItems"
        :user-name="currentUser"
        :avatar-url="currentAvatarUrl"
        @logout="handleLogout"
        @select="handleNavSelect"
      >
        <component :is="currentPageComponent.component" v-bind="currentPageComponent.props" />
      </AppSidebarLayout>
    </div>
  </div>
</template>

<script setup>
import axios from "axios";
import { computed, defineComponent, h, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import AppSidebarLayout from "./components/AppSidebarLayout.vue";
import backgroundImage from "./assets/imgs/background.png";
import AirQualityDataBrowse from "./pages/AirQualityDataBrowse.vue";
import AqiIndexPredict from "./pages/AqiIndexPredict.vue";
import DataAnalysisVisualization from "./pages/DataAnalysisVisualization.vue";
import HomeDashboard from "./pages/HomeDashboard.vue";
import PersonalCenter from "./pages/PersonalCenter.vue";
import WeatherDataBrowse from "./pages/WeatherDataBrowse.vue";

const API_BASE_URL = "/api/auth";
const AUTH_STORAGE_KEY = "ems_auth_state";

function createLineIcon(name, shapes) {
  return defineComponent({
    name,
    setup() {
      return () =>
        h(
          "svg",
          {
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            "stroke-width": "2",
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
          },
          shapes.map((shape) => h(shape.tag, shape.attrs)),
        );
    },
  });
}

const HomeNavIcon = createLineIcon("HomeNavIcon", [
  { tag: "path", attrs: { d: "M3 11.5L12 4l9 7.5" } },
  { tag: "path", attrs: { d: "M5 10.5V20h14v-9.5" } },
  { tag: "path", attrs: { d: "M10 20v-5h4v5" } },
]);
const VideoNavIcon = createLineIcon("VideoNavIcon", [
  { tag: "rect", attrs: { x: "3", y: "7", width: "14", height: "10", rx: "2" } },
  { tag: "path", attrs: { d: "M17 10l4-2v8l-4-2z" } },
]);
const CommentNavIcon = createLineIcon("CommentNavIcon", [
  { tag: "path", attrs: { d: "M21 11a8 8 0 01-8 8 8.7 8.7 0 01-3-.5L4 20l1.5-4.2A8 8 0 1113 19" } },
  { tag: "path", attrs: { d: "M8 11h8M8 8h6" } },
]);
const TrendNavIcon = createLineIcon("TrendNavIcon", [
  { tag: "path", attrs: { d: "M3 17h18" } },
  { tag: "path", attrs: { d: "M5 13l4-4 3 2 5-5" } },
]);
const PieNavIcon = createLineIcon("PieNavIcon", [
  { tag: "path", attrs: { d: "M12 2v10h10" } },
  { tag: "path", attrs: { d: "M21.2 14A9.2 9.2 0 1110 2.2" } },
]);
const BranchNavIcon = createLineIcon("BranchNavIcon", [
  { tag: "path", attrs: { d: "M6 3v18" } },
  { tag: "circle", attrs: { cx: "6", cy: "6", r: "2" } },
  { tag: "circle", attrs: { cx: "18", cy: "8", r: "2" } },
  { tag: "circle", attrs: { cx: "18", cy: "18", r: "2" } },
  { tag: "path", attrs: { d: "M8 6h6a4 4 0 014 4v0" } },
  { tag: "path", attrs: { d: "M8 6h4a6 6 0 016 6v6" } },
]);
const CloudNavIcon = createLineIcon("CloudNavIcon", [
  { tag: "path", attrs: { d: "M6 17h11a4 4 0 000-8 6 6 0 00-11.4 1A4 4 0 006 17z" } },
]);
const MapNavIcon = createLineIcon("MapNavIcon", [
  { tag: "path", attrs: { d: "M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z" } },
  { tag: "path", attrs: { d: "M9 4v14M15 6v14" } },
  { tag: "circle", attrs: { cx: "15", cy: "9", r: "2" } },
]);
const LikeNavIcon = createLineIcon("LikeNavIcon", [
  { tag: "path", attrs: { d: "M8 11V7a3 3 0 016 0v4" } },
  { tag: "path", attrs: { d: "M5 11h14l-1 9H6z" } },
]);
const ClusterNavIcon = createLineIcon("ClusterNavIcon", [
  { tag: "rect", attrs: { x: "4", y: "4", width: "8", height: "8", rx: "2" } },
  { tag: "rect", attrs: { x: "12", y: "12", width: "8", height: "8", rx: "2" } },
  { tag: "path", attrs: { d: "M12 8h2a4 4 0 014 4v0" } },
]);

const activeNav = ref("home");
const activeTab = ref("login");
const loginPortal = ref("user");
const currentUser = ref("管理员");
const currentAvatarUrl = ref("");
const isAdminIdentity = ref(false);
const isAuthenticated = ref(false);
const particles = ref([]);
const ticker = reactive({ aqi: 42, pm25: "18.0", temp: "24.3" });
const toast = reactive({
  show: false,
  message: "",
  background: "linear-gradient(135deg,#1f7f74,#4d94b8)",
});

const userSidebarItems = [
  {
    key: "group-home",
    label: "首页",
    children: [{ key: "home", label: "主页", icon: HomeNavIcon }],
  },
  {
    key: "group-browse",
    label: "数据浏览",
    children: [
      { key: "video-browse", label: "天气数据浏览", icon: VideoNavIcon },
      { key: "comment-browse", label: "空气质量数据浏览", icon: CommentNavIcon },
    ],
  },
  {
    key: "group-visual",
    label: "数据分析可视化",
    children: [
      { key: "analysis_city_diff", label: "城市空气质量差异分析", icon: TrendNavIcon },
      { key: "analysis_time_series", label: "空气质量时序变化分析", icon: PieNavIcon },
      { key: "analysis_season_cycle", label: "空气质量季节周期分析", icon: BranchNavIcon },
      { key: "analysis_weather_impact", label: "气象条件影响分析", icon: CloudNavIcon },
      { key: "analysis_pollutant_relation", label: "污染物协同关系分析", icon: MapNavIcon },
    ],
  },
  {
    key: "group-predict",
    label: "数据预测",
    children: [{ key: "aqi-predict", label: "AQI指数预测", icon: LikeNavIcon }],
  },
  {
    key: "group-user",
    label: "账户",
    children: [{ key: "profile", label: "个人中心", icon: ClusterNavIcon }],
  },
];
const adminSidebarItems = [
  {
    key: "admin-group-main",
    label: "系统导航",
    children: [
      { key: "home", label: "首页", icon: HomeNavIcon },
      { key: "weather-manage", label: "天气数据管理", icon: VideoNavIcon },
      { key: "air-manage", label: "空气质量数据管理", icon: CommentNavIcon },
      { key: "profile", label: "个人中心", icon: ClusterNavIcon },
    ],
  },
];
const sidebarItems = computed(() => (loginPortal.value === "admin" ? adminSidebarItems : userSidebarItems));

const loginForm = reactive({ username: "", password: "", remember: false });
const registerForm = reactive({ username: "", email: "", password: "", confirmPassword: "" });

const strength = ref({ width: "0%", background: "#d65d53", text: "" });
let authTimer = null;
let toastTimer = null;
let tickerTimer = null;

const strengthStyle = computed(() => ({
  width: strength.value.width,
  background: strength.value.background,
}));
const strengthText = computed(() => strength.value.text);
const currentPageComponent = computed(() => {
  if (loginPortal.value === "admin") {
    if (activeNav.value === "weather-manage") {
      return { component: WeatherDataBrowse, props: { isAdminPortal: true } };
    }
    if (activeNav.value === "air-manage") {
      return { component: AirQualityDataBrowse, props: { isAdminPortal: true } };
    }
    if (activeNav.value === "profile") {
      return {
        component: PersonalCenter,
        props: {
          userName: currentUser.value,
          isAdminPortal: true,
          onNotify: showToast,
          onProfileChange: handleProfileAvatarChange,
        },
      };
    }
    return {
      component: HomeDashboard,
      props: {
        isAdminPortal: true,
        onQuickNav: handleNavSelect,
      },
    };
  }

  if (activeNav.value === "video-browse") {
    return { component: WeatherDataBrowse, props: { isAdminPortal: false } };
  }
  if (activeNav.value === "comment-browse") {
    return { component: AirQualityDataBrowse, props: { isAdminPortal: false } };
  }
  if (activeNav.value === "aqi-predict") {
    return { component: AqiIndexPredict, props: {} };
  }
  if (activeNav.value === "profile") {
    return {
      component: PersonalCenter,
      props: {
        userName: currentUser.value,
        isAdminPortal: false,
        onNotify: showToast,
        onProfileChange: handleProfileAvatarChange,
      },
    };
  }
  if (activeNav.value.startsWith("analysis_")) {
    return { component: DataAnalysisVisualization, props: { activeNav: activeNav.value } };
  }
  return {
    component: HomeDashboard,
    props: {
      isAdminPortal: false,
      onQuickNav: handleNavSelect,
    },
  };
});

function switchTab(tab) {
  activeTab.value = tab;
}

function switchPortal(portal) {
  loginPortal.value = portal;
  activeTab.value = "login";
}

function persistAuthState(remember) {
  const payload = JSON.stringify({
    username: currentUser.value,
    avatarUrl: currentAvatarUrl.value,
    activeNav: activeNav.value,
    portal: loginPortal.value,
    is_admin: isAdminIdentity.value,
  });
  if (remember) {
    localStorage.setItem(AUTH_STORAGE_KEY, payload);
    sessionStorage.removeItem(AUTH_STORAGE_KEY);
    return;
  }
  sessionStorage.setItem(AUTH_STORAGE_KEY, payload);
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

function clearAuthState() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
  sessionStorage.removeItem(AUTH_STORAGE_KEY);
}

function restoreAuthState() {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY) || sessionStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return;
  }
  try {
    const auth = JSON.parse(raw);
    if (!auth?.username) {
      clearAuthState();
      return;
    }
    currentUser.value = auth.username;
    currentAvatarUrl.value = auth.avatarUrl || "";
    loginPortal.value = auth.portal === "admin" ? "admin" : "user";
    isAdminIdentity.value = Boolean(auth.is_admin);
    activeNav.value = auth.activeNav || "home";
    isAuthenticated.value = true;
  } catch (error) {
    clearAuthState();
  }
}

async function fetchCurrentProfile() {
  if (!currentUser.value) {
    return;
  }
  try {
    const { data } = await axios.get(`${API_BASE_URL}/profile/`, {
      params: { username: currentUser.value },
    });
    const avatarUrl = data?.data?.avatar_url || "";
    currentAvatarUrl.value = avatarUrl;
    const remembered = Boolean(localStorage.getItem(AUTH_STORAGE_KEY));
    persistAuthState(remembered);
  } catch (error) {
    // ignore profile fetch error in shell-level refresh
  }
}

function handleProfileAvatarChange(url) {
  currentAvatarUrl.value = url || "";
  const remembered = Boolean(localStorage.getItem(AUTH_STORAGE_KEY));
  persistAuthState(remembered);
}

function showToast(message, success = true) {
  toast.message = message;
  toast.background = success
    ? "linear-gradient(135deg,#1f7f74,#4d94b8)"
    : "linear-gradient(135deg,#d65d53,#d09e54)";
  toast.show = true;
  if (toastTimer) {
    clearTimeout(toastTimer);
  }
  toastTimer = setTimeout(() => {
    toast.show = false;
  }, 2800);
}

function checkStrength() {
  const val = registerForm.password;
  if (!val.length) {
    strength.value = { width: "0%", background: "#d65d53", text: "" };
    return;
  }

  let score = 0;
  if (val.length >= 8) score += 1;
  if (/[A-Z]/.test(val)) score += 1;
  if (/[0-9]/.test(val)) score += 1;
  if (/[^A-Za-z0-9]/.test(val)) score += 1;

  const levels = [
    { width: "20%", background: "#d65d53", text: "强度：弱" },
    { width: "45%", background: "#d09e54", text: "强度：一般" },
    { width: "70%", background: "#4d94b8", text: "强度：良好" },
    { width: "100%", background: "#1f7f74", text: "强度：强" },
  ];

  strength.value = levels[Math.max(0, score - 1)];
}

async function handleLogin(event) {
  createRipple(event);

  if (!loginForm.username.trim() || !loginForm.password) {
    showToast("请填写完整登录信息", false);
    return;
  }

  try {
    const apiPath = loginPortal.value === "admin" ? "admin-login" : "login";
    const response = await axios.post(`${API_BASE_URL}/${apiPath}/`, {
      username: loginForm.username.trim(),
      password: loginForm.password,
    });

    currentUser.value = response?.data?.username || loginForm.username.trim();
    isAdminIdentity.value = Boolean(response?.data?.is_staff || response?.data?.is_superuser);
    showToast(`✓ ${response.data.message}，欢迎 ${currentUser.value}`);

    if (authTimer) {
      clearTimeout(authTimer);
    }
    authTimer = setTimeout(() => {
      activeNav.value = "home";
      isAuthenticated.value = true;
      persistAuthState(Boolean(loginForm.remember));
      fetchCurrentProfile();
    }, 500);
  } catch (error) {
    const message = error?.response?.data?.message || "登录失败，请稍后重试";
    showToast(message, false);
  }
}

async function handleRegister(event) {
  createRipple(event);

  if (
    !registerForm.username.trim() ||
    !registerForm.email.trim() ||
    !registerForm.password ||
    !registerForm.confirmPassword
  ) {
    showToast("请填写完整注册信息", false);
    return;
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    showToast("两次密码输入不一致", false);
    return;
  }
  if (registerForm.password.length < 8) {
    showToast("密码至少需要8位", false);
    return;
  }

  try {
    const response = await axios.post(`${API_BASE_URL}/register/`, {
      username: registerForm.username.trim(),
      password: registerForm.password,
    });
    showToast(`✓ ${response.data.message}`);
    registerForm.password = "";
    registerForm.confirmPassword = "";
    checkStrength();
    setTimeout(() => {
      switchTab("login");
    }, 1400);
  } catch (error) {
    const message = error?.response?.data?.message || "注册失败，请稍后重试";
    showToast(message, false);
  }
}

function handleLogout() {
  isAuthenticated.value = false;
  activeTab.value = "login";
  loginForm.password = "";
  currentAvatarUrl.value = "";
  isAdminIdentity.value = false;
  clearAuthState();
  showToast("已退出登录");
}

function handleNavSelect(key) {
  activeNav.value = key;
}

function togglePortalMode() {
  loginPortal.value = loginPortal.value === "admin" ? "user" : "admin";
  activeNav.value = "home";
  const remembered = Boolean(localStorage.getItem(AUTH_STORAGE_KEY));
  persistAuthState(remembered);
}

function createRipple(event) {
  const button = event.currentTarget;
  if (!button) {
    return;
  }

  const ripple = document.createElement("span");
  ripple.className = "btn-ripple";
  const size = Math.max(button.offsetWidth, button.offsetHeight);
  const rect = button.getBoundingClientRect();
  ripple.style.width = `${size}px`;
  ripple.style.height = `${size}px`;
  ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
  ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
  button.appendChild(ripple);
  setTimeout(() => ripple.remove(), 700);
}

function spawnParticles() {
  const colors = [
    "rgba(31,127,116,0.45)",
    "rgba(77,148,184,0.36)",
    "rgba(208,158,84,0.28)",
    "rgba(255,255,255,0.55)",
  ];

  particles.value = Array.from({ length: 28 }, (_, index) => {
    const size = Math.random() * 10 + 4;
    return {
      id: index,
      style: {
        width: `${size}px`,
        height: `${size}px`,
        left: `${Math.random() * 100}%`,
        bottom: `${-20 + Math.random() * 20}px`,
        background: colors[Math.floor(Math.random() * colors.length)],
        animationDuration: `${8 + Math.random() * 12}s`,
        animationDelay: `${Math.random() * 10}s`,
      },
    };
  });
}

function updateTicker() {
  const rand = (base, range) => (base + (Math.random() - 0.5) * range).toFixed(1);
  ticker.aqi = Math.round(38 + Math.random() * 12);
  ticker.pm25 = rand(17, 6);
  ticker.temp = rand(24, 3);
}

onMounted(() => {
  restoreAuthState();
  if (isAuthenticated.value) {
    fetchCurrentProfile();
  }
  spawnParticles();
  tickerTimer = setInterval(updateTicker, 3000);
});

onBeforeUnmount(() => {
  if (authTimer) clearTimeout(authTimer);
  if (toastTimer) clearTimeout(toastTimer);
  if (tickerTimer) clearInterval(tickerTimer);
});
</script>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@300;400;600;700&family=Noto+Sans+SC:wght@300;400;500&family=Rajdhani:wght@300;400;500;600;700&display=swap");

:root {
  --teal: #2f6d57;
  --sky: #4f7f65;
  --gold: #d09e54;
  --text-dark: #233c2f;
  --text-mid: #365b49;
  --text-light: #617b6b;
  --glass: #d9e4d6;
  --glass-border: #a6bda9;
  --shadow: 0 20px 56px rgba(22, 46, 33, 0.22);
}

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body {
  height: 100%;
  font-family: "Noto Sans SC", sans-serif;
  color: var(--text-dark);
  overflow-x: hidden;
}

.app-shell {
  min-height: 100vh;
}

.workspace-shell {
  position: relative;
  min-height: 100vh;
}

.portal-jump-btn {
  position: fixed;
  right: 26px;
  top: 16px;
  z-index: 60;
  border: 1px solid #d3e0ea;
  background: rgba(255, 255, 255, 0.94);
  color: #234f61;
  border-radius: 10px;
  height: 38px;
  padding: 0 14px;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(30, 65, 85, 0.12);
}

.bg-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  background-color: #8eb6b2;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  transform: scale(1.02);
}

.bg-overlay {
  position: fixed;
  inset: 0;
  z-index: 1;
  display: block;
  background: linear-gradient(180deg, rgba(22, 48, 35, 0.24) 0%, rgba(22, 48, 35, 0.16) 100%);
}

.particles {
  position: fixed;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  overflow: hidden;
  display: none;
}

.particle {
  position: absolute;
  border-radius: 50%;
  opacity: 0;
  animation: floatUp linear infinite;
}

@keyframes floatUp {
  0% {
    transform: translateY(0) translateX(0) scale(1);
    opacity: 0;
  }
  10% {
    opacity: 0.6;
  }
  90% {
    opacity: 0.3;
  }
  100% {
    transform: translateY(-110vh) translateX(30px) scale(0.6);
    opacity: 0;
  }
}

.scan-line {
  position: fixed;
  left: 0;
  right: 0;
  height: 2px;
  z-index: 3;
  pointer-events: none;
  background: linear-gradient(90deg, transparent, rgba(31, 127, 116, 0.4), transparent);
  animation: scan 6s ease-in-out infinite;
  display: none;
}

@keyframes scan {
  0% {
    top: -4px;
    opacity: 0;
  }
  5% {
    opacity: 1;
  }
  95% {
    opacity: 1;
  }
  100% {
    top: 100vh;
    opacity: 0;
  }
}

.page {
  position: relative;
  z-index: 10;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
}

.card {
  width: 100%;
  max-width: 520px;
  background: #cddbcf;
  border: 1px solid #95ae98;
  border-radius: 22px;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  box-shadow: 0 20px 44px rgba(22, 46, 33, 0.28);
  overflow: hidden;
  animation: riseCard 0.9s cubic-bezier(0.22, 0.68, 0, 1.2) 0.15s both;
}

@keyframes riseCard {
  from {
    opacity: 0;
    transform: translateY(40px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.card-hero {
  position: relative;
  padding: 24px 28px 18px;
  overflow: hidden;
  background: linear-gradient(90deg, #c4d6c5 0%, #b8ccb9 100%);
  border-bottom: 1px solid rgba(31, 127, 116, 0.14);
  animation: fadeDown 0.9s cubic-bezier(0.22, 0.68, 0, 1.2) both;
}

.card-hero::before {
  content: "";
  position: absolute;
  inset: 0;
  background: none;
  pointer-events: none;
}

@keyframes fadeDown {
  from {
    opacity: 0;
    transform: translateY(-32px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.site-logo {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 14px;
}

.hero-text {
  min-width: 0;
}

.logo-icon {
  width: 52px;
  height: 52px;
  background: linear-gradient(135deg, var(--teal), var(--sky));
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 24px rgba(31, 127, 116, 0.28);
  position: relative;
  overflow: hidden;
}

.logo-icon::after {
  content: "";
  position: absolute;
  width: 200%;
  height: 200%;
  top: -50%;
  left: -150%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0% {
    left: -150%;
  }
  100% {
    left: 150%;
  }
}

.logo-icon svg {
  width: 28px;
  height: 28px;
  fill: none;
  stroke: #fff;
  stroke-width: 2;
  position: relative;
  z-index: 1;
}

.site-title {
  font-family: "Noto Serif SC", serif;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #294636;
  text-shadow: none;
  white-space: nowrap;
}

.tabs {
  display: flex;
  border-bottom: 1px solid rgba(31, 127, 116, 0.12);
  position: relative;
  background: #c7d5c8;
}

.portal-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.portal-switch--inline {
  margin: 4px 0 14px;
}

.portal-switch__btn {
  border: 1px solid #8ea88f;
  background: #e3ebe1;
  color: #315846;
  height: 36px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}

.portal-switch__btn.active {
  background: linear-gradient(135deg, #bfd3c4, #a9c2b0);
  border-color: #7f9f87;
  color: #254a38;
}

.tabs--single .tab-btn {
  flex: 1;
}

.tab-btn {
  flex: 1;
  background: none;
  border: none;
  cursor: pointer;
  padding: 16px 0 14px;
  font-family: "Noto Serif SC", serif;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 3px;
  color: var(--text-mid);
  transition: color 0.3s;
}

.tab-btn.active {
  color: var(--teal);
}

.tab-indicator {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 2.5px;
  width: 50%;
  background: linear-gradient(90deg, var(--teal), var(--sky));
  border-radius: 2px;
  transition: transform 0.4s cubic-bezier(0.22, 0.68, 0, 1.2);
}

.tabs[data-active="register"] .tab-indicator {
  transform: translateX(100%);
}

.forms-wrap {
  position: relative;
  overflow: hidden;
  background: #cddbcf;
}

.form-panel {
  padding: 28px 36px 34px;
  width: 100%;
  background: #cddbcf;
  transition: transform 0.5s cubic-bezier(0.22, 0.68, 0, 1.2), opacity 0.4s;
  position: relative;
}

.form-panel.hidden {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  opacity: 0;
  pointer-events: none;
}

#login-form.hidden {
  transform: translateX(-60px);
}

#register-form.hidden {
  transform: translateX(60px);
}

#login-form:not(.hidden),
#register-form:not(.hidden) {
  transform: translateX(0);
  opacity: 1;
}

.input-group {
  margin-bottom: 22px;
}

.input-label {
  display: block;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: var(--text-mid);
  margin-bottom: 8px;
}

.input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 16px;
  width: 18px;
  height: 18px;
  color: var(--text-light);
  transition: color 0.25s;
  pointer-events: none;
}

.input-wrap input {
  width: 100%;
  padding: 14px 18px 14px 46px;
  background: #edf3ea;
  border: 1.5px solid #9eb4a3;
  border-radius: 12px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: var(--text-dark);
  outline: none;
  transition: border-color 0.25s, box-shadow 0.25s, background 0.25s;
}

.input-wrap input::placeholder {
  color: #6a8785;
}

.input-wrap input:focus {
  border-color: var(--teal);
  background: #f5faf3;
  box-shadow: 0 0 0 4px rgba(31, 127, 116, 0.08);
}

.input-wrap:focus-within .input-icon {
  color: var(--teal);
}

.strength-wrap {
  margin-top: 8px;
  display: none;
}

.strength-bar {
  height: 4px;
  background: rgba(31, 127, 116, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 4px;
  width: 0%;
  transition: width 0.4s, background 0.4s;
}

.strength-text {
  font-size: 10px;
  letter-spacing: 1px;
  margin-top: 4px;
}

.row-extra {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-mid);
  cursor: pointer;
  user-select: none;
}

.checkbox-label input {
  display: none;
}

.custom-check {
  width: 18px;
  height: 18px;
  border: 1.5px solid rgba(31, 127, 116, 0.34);
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, border-color 0.2s;
  flex-shrink: 0;
}

.checkbox-label input:checked ~ .custom-check {
  background: var(--teal);
  border-color: var(--teal);
}

.custom-check svg {
  width: 10px;
  height: 10px;
  stroke: #fff;
  stroke-width: 3;
  display: none;
}

.checkbox-label input:checked ~ .custom-check svg {
  display: block;
}

.forgot-link {
  font-size: 12px;
  color: var(--teal);
  text-decoration: none;
  letter-spacing: 0.5px;
  transition: opacity 0.2s;
}

.forgot-link:hover {
  opacity: 0.7;
}

.btn-submit {
  width: 100%;
  padding: 14px;
  background: linear-gradient(135deg, var(--teal) 0%, var(--sky) 100%);
  border: none;
  border-radius: 14px;
  font-family: "Noto Serif SC", serif;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 3px;
  color: #fff;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  box-shadow: 0 10px 24px rgba(24, 57, 40, 0.28);
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-submit:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 36px rgba(31, 127, 116, 0.36);
}

.btn-submit:active {
  transform: translateY(0);
}

.btn-submit .btn-ripple {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.35);
  transform: scale(0);
  animation: ripple 0.6s linear;
  pointer-events: none;
}

@keyframes ripple {
  to {
    transform: scale(4);
    opacity: 0;
  }
}

.btn-submit .btn-shine {
  position: absolute;
  top: 0;
  left: -100%;
  width: 60%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.25), transparent);
  transform: skewX(-20deg);
  transition: left 0.6s;
}

.btn-submit:hover .btn-shine {
  left: 150%;
}

.agree-text {
  font-size: 11px;
  color: #50706e;
  text-align: center;
  margin-top: 20px;
  line-height: 1.8;
}

.agree-text a {
  color: var(--teal);
  text-decoration: none;
}

.site-footer {
  margin-top: 32px;
  text-align: center;
  font-family: "Rajdhani", sans-serif;
  font-size: 12px;
  letter-spacing: 3px;
  color: rgba(28, 77, 72, 0.66);
  animation: fadeUp 1s 0.4s both;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.toast {
  position: fixed;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%) translateY(20px);
  color: #fff;
  padding: 12px 28px;
  border-radius: 40px;
  font-size: 13px;
  letter-spacing: 1px;
  box-shadow: 0 8px 30px rgba(31, 127, 116, 0.24);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s, transform 0.3s;
  z-index: 999;
}

.toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

.deco-ring {
  position: fixed;
  border-radius: 50%;
  border: 1.5px solid rgba(245, 249, 250, 0.16);
  pointer-events: none;
  z-index: 2;
  display: none;
}

@keyframes spinRing {
  to {
    transform: rotate(360deg);
  }
}

.deco-ring-1 {
  width: 520px;
  height: 520px;
  top: -140px;
  right: -160px;
  animation-duration: 30s;
}

.deco-ring-2 {
  width: 320px;
  height: 320px;
  bottom: -80px;
  left: -100px;
  animation-duration: 22s;
  animation-direction: reverse;
  border-color: rgba(77, 148, 184, 0.14);
}

.deco-dot {
  position: fixed;
  z-index: 2;
  pointer-events: none;
  border-radius: 50%;
  display: none;
}

.deco-dot-1 {
  width: 300px;
  height: 300px;
  top: -60px;
  left: -60px;
}

.deco-dot-2 {
  width: 200px;
  height: 200px;
  bottom: 20px;
  right: 60px;
  background: radial-gradient(circle, rgba(77, 148, 184, 0.14), transparent 70%);
}

.ticker {
  position: fixed;
  top: 20px;
  right: 24px;
  z-index: 20;
  display: none;
  flex-direction: column;
  gap: 6px;
  animation: fadeUp 1s 0.8s both;
}

.ticker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(238, 250, 247, 0.72);
  border: 1px solid rgba(187, 224, 216, 0.7);
  border-radius: 40px;
  padding: 6px 14px;
  backdrop-filter: blur(10px);
}

.ticker-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  animation: blink 1.5s ease-in-out infinite;
}

@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

.ticker-label {
  font-family: "Rajdhani", sans-serif;
  font-size: 11px;
  letter-spacing: 2px;
  color: #2b6460;
}

.ticker-value {
  font-family: "Rajdhani", sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #1f504c;
}

@media (max-width: 980px) {
  .page {
    padding: 20px 12px;
  }
}

@media (max-width: 560px) {
  .form-panel {
    padding: 28px 24px 32px;
  }

  .site-logo {
    align-items: center;
  }

  .card-hero {
    padding: 24px 22px 20px;
  }

  .site-title {
    font-size: 18px;
    white-space: normal;
  }

  .ticker {
    display: none;
  }

  .row-extra {
    gap: 12px;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

