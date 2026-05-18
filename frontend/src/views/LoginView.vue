<template>
  <div class="login-bg">
    <div class="login-card">
      <div class="login-header">
        <el-icon :size="48" color="#1677ff"><Cloudy /></el-icon>
        <h1>智水调度助手</h1>
        <p>基于AI Agent的泵站能效优化调度系统</p>
      </div>
      <el-form :model="form" @submit.prevent="handleLogin" size="large">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码"
                    prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleLogin" style="width:100%">
            登 录
          </el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="handleRegister" style="width:100%">注 册</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await login(form)
    userStore.setUser(data)
    ElMessage.success('登录成功')
    router.push('/')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await register(form)
    userStore.setUser(data)
    ElMessage.success('注册成功')
    router.push('/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-bg {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
  padding: 40px 36px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0,0,0,.15);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-header h1 {
  font-size: 24px;
  color: #1d1d1f;
  margin: 12px 0 4px;
}
.login-header p {
  font-size: 13px;
  color: #86868b;
}
</style>
