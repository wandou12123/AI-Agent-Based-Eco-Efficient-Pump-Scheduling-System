import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

/** 解包统一响应 { success, data } */
function unwrapResponse(data: any) {
  if (data && typeof data === 'object' && 'success' in data) {
    if (data.success === false) {
      const msg = data.error?.message || data.detail || '请求失败'
      throw Object.assign(new Error(msg), { response: { data, status: 400 } })
    }
    return data.data
  }
  return data
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => {
    res.data = unwrapResponse(res.data)
    return res
  },
  (err) => {
    const raw = err.response?.data
    const msg = raw?.error?.message || raw?.detail || err.message || '请求失败'
    ElMessage.error(msg)
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.hash = '#/login'
    }
    return Promise.reject(err)
  }
)

export default api
