<template>
  <section class="profile-page">
    <header class="profile-page__head">
      <h2>个人中心</h2>
      <p>{{ isAdminPortal ? "后台管理员信息维护" : "账户信息维护" }}</p>
    </header>

    <div class="profile-grid">
      <article class="panel panel--avatar">
        <h3>头像</h3>
        <div class="avatar-wrap">
          <img v-if="profile.avatarUrl" :src="profile.avatarUrl" alt="avatar" class="avatar-img" />
          <div v-else class="avatar-fallback">{{ avatarText }}</div>
        </div>
        <label class="upload-btn">
          本地上传头像
          <input type="file" accept="image/*" @change="handleAvatarChange" />
        </label>
      </article>

      <article class="panel">
        <h3>个人信息</h3>
        <div class="field-grid">
          <label class="field">
            <span>用户名</span>
            <input :value="profile.username" disabled />
          </label>
          <label class="field">
            <span>显示名称</span>
            <input v-model.trim="profile.displayName" maxlength="64" />
          </label>
          <label class="field">
            <span>邮箱</span>
            <input v-model.trim="profile.email" type="email" maxlength="254" />
          </label>
          <label class="field">
            <span>手机号</span>
            <input v-model.trim="profile.phone" maxlength="32" />
          </label>
          <label class="field field--full">
            <span>个人简介</span>
            <textarea v-model.trim="profile.bio" maxlength="255"></textarea>
          </label>
        </div>
        <button class="action-btn" type="button" @click="saveProfile">保存信息</button>
      </article>
    </div>

    <article class="panel">
      <h3>修改密码</h3>
      <div class="field-grid pwd-grid">
        <label class="field">
          <span>原密码</span>
          <input v-model="passwordForm.oldPassword" type="password" />
        </label>
        <label class="field">
          <span>新密码</span>
          <input v-model="passwordForm.newPassword" type="password" />
        </label>
        <label class="field">
          <span>确认新密码</span>
          <input v-model="passwordForm.confirmPassword" type="password" />
        </label>
      </div>
      <button class="action-btn" type="button" @click="changePassword">修改密码</button>
    </article>
  </section>
</template>

<script setup>
import axios from "axios";
import { computed, onMounted, reactive } from "vue";

const API_BASE_URL = "/api/auth";

const props = defineProps({
  userName: {
    type: String,
    default: "",
  },
  isAdminPortal: {
    type: Boolean,
    default: false,
  },
  onNotify: {
    type: Function,
    default: null,
  },
  onProfileChange: {
    type: Function,
    default: null,
  },
});

const profile = reactive({
  username: "",
  email: "",
  displayName: "",
  phone: "",
  bio: "",
  avatarUrl: "",
});

const passwordForm = reactive({
  oldPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const avatarText = computed(() => {
  const name = (profile.displayName || profile.username || "U").trim();
  return name.charAt(0).toUpperCase();
});

function notify(message, ok = true) {
  if (props.onNotify) {
    props.onNotify(message, ok);
  }
}

function pushProfileChange() {
  if (props.onProfileChange) {
    props.onProfileChange(profile.avatarUrl || "");
  }
}

function normalizeAvatar(url) {
  if (!url) {
    return "";
  }
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  return `${window.location.origin}${url}`;
}

async function fetchProfile() {
  if (!props.userName) {
    return;
  }
  try {
    const { data } = await axios.get(`${API_BASE_URL}/profile/`, {
      params: { username: props.userName },
    });
    const info = data?.data || {};
    profile.username = info.username || props.userName;
    profile.email = info.email || "";
    profile.displayName = info.display_name || "";
    profile.phone = info.phone || "";
    profile.bio = info.bio || "";
    profile.avatarUrl = normalizeAvatar(info.avatar_url || "");
    pushProfileChange();
  } catch (error) {
    notify(error?.response?.data?.message || "加载个人信息失败", false);
  }
}

async function saveProfile() {
  try {
    const { data } = await axios.post(`${API_BASE_URL}/profile/`, {
      username: props.userName,
      email: profile.email,
      display_name: profile.displayName,
      phone: profile.phone,
      bio: profile.bio,
    });
    const info = data?.data || {};
    profile.avatarUrl = normalizeAvatar(info.avatar_url || profile.avatarUrl);
    pushProfileChange();
    notify("个人信息已保存");
  } catch (error) {
    notify(error?.response?.data?.message || "保存失败", false);
  }
}

async function changePassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword || !passwordForm.confirmPassword) {
    notify("请完整填写密码信息", false);
    return;
  }
  if (passwordForm.newPassword.length < 6) {
    notify("新密码至少6位", false);
    return;
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    notify("两次新密码输入不一致", false);
    return;
  }
  try {
    const { data } = await axios.post(`${API_BASE_URL}/change-password/`, {
      username: props.userName,
      old_password: passwordForm.oldPassword,
      new_password: passwordForm.newPassword,
    });
    passwordForm.oldPassword = "";
    passwordForm.newPassword = "";
    passwordForm.confirmPassword = "";
    notify(data?.message || "密码修改成功");
  } catch (error) {
    notify(error?.response?.data?.message || "密码修改失败", false);
  }
}

async function handleAvatarChange(event) {
  const file = event?.target?.files?.[0];
  if (!file) {
    return;
  }
  const formData = new FormData();
  formData.append("username", props.userName);
  formData.append("avatar", file);

  try {
    const { data } = await axios.post(`${API_BASE_URL}/upload-avatar/`, formData);
    const url = data?.data?.avatar_url || "";
    profile.avatarUrl = normalizeAvatar(url);
    pushProfileChange();
    notify("头像上传成功");
  } catch (error) {
    notify(error?.response?.data?.message || "头像上传失败", false);
  } finally {
    event.target.value = "";
  }
}

onMounted(fetchProfile);
</script>

<style scoped>
.profile-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.profile-page__head h2 {
  margin: 0 0 4px;
  font-size: 30px;
  color: #16343d;
  letter-spacing: 0.5px;
}

.profile-page__head p {
  margin: 0;
  color: #5b7482;
}

.profile-grid {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 14px;
}

.panel {
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #d7e3ea;
  padding: 16px;
  box-shadow: 0 10px 24px rgba(20, 56, 74, 0.06);
}

.panel h3 {
  margin: 0 0 14px;
  color: #214958;
  font-size: 18px;
}

.panel--avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.avatar-wrap {
  width: 128px;
  height: 128px;
  border-radius: 50%;
  overflow: hidden;
  border: 3px solid #d7e4ec;
  background: #edf4f8;
  margin-bottom: 16px;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48px;
  color: #2b6070;
  font-weight: 700;
}

.upload-btn {
  height: 38px;
  padding: 0 14px;
  border-radius: 10px;
  background: #eff6fb;
  border: 1px solid #c7d8e4;
  color: #1f4b5b;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.upload-btn input {
  display: none;
}

.field-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field--full {
  grid-column: 1 / -1;
}

.field span {
  color: #56707e;
  font-size: 13px;
}

.field input,
.field textarea {
  min-height: 40px;
  border: 1px solid #d2dee7;
  border-radius: 10px;
  padding: 8px 12px;
  outline: none;
  font-size: 14px;
  background: #fbfdff;
}

.field textarea {
  min-height: 72px;
  resize: vertical;
}

.field input:focus,
.field textarea:focus {
  border-color: #76a3bc;
  box-shadow: 0 0 0 3px rgba(118, 163, 188, 0.12);
}

.pwd-grid {
  grid-template-columns: 1fr 1fr 1fr;
}

.action-btn {
  border: none;
  border-radius: 10px;
  height: 40px;
  min-width: 124px;
  padding: 0 16px;
  background: linear-gradient(120deg, #255f7a, #3d7f9f);
  color: #fff;
  cursor: pointer;
}

@media (max-width: 1080px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .pwd-grid {
    grid-template-columns: 1fr;
  }
}
</style>

