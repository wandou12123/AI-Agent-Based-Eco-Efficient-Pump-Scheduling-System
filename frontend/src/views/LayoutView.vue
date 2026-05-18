<template>
  <el-container style="height:100vh">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <el-icon :size="28" color="#1677ff"><Cloudy /></el-icon>
        <span>智水调度</span>
      </div>
      <el-menu :default-active="activeMenu" router background-color="#001529"
               text-color="#ffffffcc" active-text-color="#1677ff">
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI 对话</span>
        </el-menu-item>
        <el-menu-item index="/schedule">
          <el-icon><DataAnalysis /></el-icon>
          <span>调度面板</span>
        </el-menu-item>
        <el-menu-item index="/station">
          <el-icon><Monitor /></el-icon>
          <span>泵站监控</span>
        </el-menu-item>
        <el-menu-item index="/config">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="top-header">
        <span class="header-title">基于AI Agent的泵站能效优化调度系统</span>
        <div class="header-right">
          <el-icon :size="18"><User /></el-icon>
          <span style="margin:0 12px 0 6px">{{ userStore.username }}</span>
          <el-button text type="danger" @click="handleLogout">退出</el-button>
        </div>
      </el-header>
      <el-main style="padding:16px;overflow:auto">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const activeMenu = computed(() => route.path)

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
  background: #001529;
  overflow-y: auto;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 20px 16px;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
}
.top-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #f0f0f0;
  padding: 0 20px;
}
.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}
.header-right {
  display: flex;
  align-items: center;
  color: #666;
}
</style>
