import { ref } from 'vue'
import { api } from '@/lib/api'

const guideCache = ref<any>(null)

export function useFirstDayGuide() {
  async function fetchFirstDayGuide() {
    if (guideCache.value) return guideCache.value
    const response = await api.get('/result-based/first-day')
    guideCache.value = response
    return response
  }

  async function fetchFirstDayProgress() {
    return api.get('/result-based/first-day')
  }

  async function completeFirstDayStep(step: number) {
    await api.post('/result-based/first-day/step', { step })
    guideCache.value = null // invalidate cache
  }

  return {
    fetchFirstDayGuide,
    fetchFirstDayProgress,
    completeFirstDayStep,
  }
}
