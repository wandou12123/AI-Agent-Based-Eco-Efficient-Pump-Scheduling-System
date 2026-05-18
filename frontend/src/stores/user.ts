import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')
  const userId = ref(Number(localStorage.getItem('userId') || 0))

  function setUser(data: { access_token: string; username: string; role: string; user_id: number }) {
    token.value = data.access_token
    username.value = data.username
    role.value = data.role
    userId.value = data.user_id
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('username', data.username)
    localStorage.setItem('role', data.role)
    localStorage.setItem('userId', String(data.user_id))
  }

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    userId.value = 0
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    localStorage.removeItem('userId')
  }

  return { token, username, role, userId, setUser, logout }
})
