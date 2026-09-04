import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import i18n from '@/composables/useI18n'
import { useAuthStore } from '@/stores/auth'
import App from './App.vue'
import { isPublicRoute, routes } from './router'
import './style.css'
import './styles/tesla-jarvis-theme.css'
import 'xterm/css/xterm.css'

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {
      // SW registration failed — non-critical
    })
  })
}

const pinia = createPinia()
const router = createRouter({
  history: createWebHistory(),
  routes,
})

const auth = useAuthStore(pinia)

function ensureDeviceId(): string {
  const key = 'CATEYE-device-id'
  try {
    const existing = localStorage.getItem(key)
    if (existing) return existing
    const id =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`
    localStorage.setItem(key, id)
    return id
  } catch {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 12)}`
  }
}

// Establish a device identity up front so autoLogin never needs email/password.
ensureDeviceId()

router.beforeEach(async (to, from, next) => {
  if (isPublicRoute(to)) {
    return next()
  }

  if (auth.isAuthenticated) {
    return next()
  }

  const loggedIn = await auth.autoLogin()
  if (loggedIn) {
    return next()
  }

  // No dedicated login page: auto-login by device is the only flow. If it fails
  // (backend down / no identity), let the route through — the API layer still
  // guards every mutation, so nothing is exposed.
  return next()
})

const app = createApp(App)
app.use(pinia)
app.use(router)
app.use(i18n)
app.mount('#app')
