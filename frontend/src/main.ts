import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import { createPinia } from 'pinia'
import App from './App.vue'
import { routes, isPublicRoute } from './router'
import { useAuthStore } from '@/stores/auth'
import './style.css'

const pinia = createPinia()
const router = createRouter({
  history: createWebHistory(),
  routes,
})

const auth = useAuthStore(pinia)

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

  return next({ name: 'login', query: { redirect: to.fullPath } })
})

const app = createApp(App)
app.use(pinia)
app.use(router)
app.mount('#app')
