<template>
  <div class="sidebar-layout" :class="{ 'sidebar-layout--collapsed': isCollapsed }">
    <aside class="sidebar-layout__aside">
      <div class="sidebar-layout__brand">
        <div class="sidebar-layout__logo" aria-hidden="true">
          <svg viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="5.6" />
            <path d="M18 3.5v4M18 28.5v4M3.5 18h4M28.5 18h4" />
            <path d="M7.5 7.5l2.8 2.8M25.7 25.7l2.8 2.8M7.5 28.5l2.8-2.8M25.7 10.3l2.8-2.8" />
          </svg>
        </div>
        <div class="sidebar-layout__brand-text">
          <h1 class="sidebar-layout__brand-name">{{ title }}</h1>
          <p v-if="subtitle" class="sidebar-layout__brand-subtitle">{{ subtitle }}</p>
        </div>
        <button
          class="sidebar-layout__menu-btn"
          type="button"
          :aria-label="isCollapsed ? '展开侧边栏' : '收起侧边栏'"
          :aria-expanded="String(!isCollapsed)"
          @click="toggleSidebar"
        >
          <span></span><span></span><span></span>
        </button>
      </div>

      <nav class="sidebar-layout__nav" aria-label="Primary">
        <section v-for="group in items" :key="group.key" class="sidebar-layout__group">
          <h2 class="sidebar-layout__group-title">{{ group.label }}</h2>
          <button
            v-for="item in group.children"
            :key="item.key"
            class="sidebar-layout__nav-btn"
            :class="{ 'is-active': item.key === activeKey }"
            type="button"
            @click="handleSelect(item.key)"
          >
            <component :is="item.icon" class="sidebar-layout__nav-icon" />
            <span class="sidebar-layout__nav-label">{{ item.label }}</span>
          </button>
        </section>
      </nav>

      <div class="sidebar-layout__footer">
        <div class="sidebar-layout__avatar" :title="userName">
          <img v-if="avatarUrl" :src="avatarUrl" alt="avatar" />
          <span v-else>{{ avatarText }}</span>
        </div>
        <button class="sidebar-layout__logout" type="button" @click="$emit('logout')">退出登录</button>
      </div>
    </aside>

    <main class="sidebar-layout__main">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

import "../styles/sidebar-layout.css";

const props = defineProps({
  activeKey: {
    type: String,
    required: true,
  },
  items: {
    type: Array,
    default: () => [],
  },
  subtitle: {
    type: String,
    default: "Environmental Monitoring System",
  },
  title: {
    type: String,
    default: "环境监测数据分析系统",
  },
  userName: {
    type: String,
    default: "管理员",
  },
  avatarUrl: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["logout", "select"]);
const isCollapsed = ref(false);
const avatarText = computed(() => {
  const name = String(props.userName || "").trim();
  return (name.charAt(0) || "U").toUpperCase();
});

function toggleSidebar() {
  isCollapsed.value = !isCollapsed.value;
}

function handleSelect(key) {
  emit("select", key);
}
</script>
