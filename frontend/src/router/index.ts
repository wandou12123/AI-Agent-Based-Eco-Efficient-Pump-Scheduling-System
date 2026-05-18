import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue') },
  {
    path: '/',
    component: () => import('../views/LayoutView.vue'),
    redirect: '/chat',
    children: [
      { path: 'chat', name: 'Chat', component: () => import('../views/ChatView.vue') },
      { path: 'schedule', name: 'Schedule', component: () => import('../views/ScheduleView.vue') },
      { path: 'station', name: 'Station', component: () => import('../views/StationView.vue') },
      { path: 'config', name: 'Config', component: () => import('../views/ConfigView.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (to.name !== 'Login' && !token) {
    next({ name: 'Login' })
  } else {
    next()
  }
})

export default router
