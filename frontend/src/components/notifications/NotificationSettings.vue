<script setup lang="ts">
/**
 * NotificationSettings — granular notification configuration.
 * 
 * Settings:
 * - Channel toggles (Desktop, Mobile, Watch, Email)
 * - Priority toggles (Critical, High, Medium, Low, Info)
 * - Feature toggles (Daily briefing, Monthly report)
 * - Quiet hours
 * - Sound and vibration
 * - Badge
 * - Retention
 */

import { X } from '@lucide/vue'
import { onMounted, ref, watch } from 'vue'
import { api } from '@/lib/api'

const emit = defineEmits<{
  close: []
}>()

const loading = ref(false)
const saving = ref(false)
const error = ref('')

// Preferences
const preferences = ref({
  desktop_enabled: true,
  mobile_enabled: true,
  watch_enabled: true,
  email_enabled: false,
  critical_enabled: true,
  high_enabled: true,
  medium_enabled: true,
  low_enabled: true,
  info_enabled: true,
  daily_briefing_enabled: true,
  monthly_report_enabled: true,
  monthly_report_email: '',
  quiet_hours_enabled: false,
  quiet_hours_start: '22:00',
  quiet_hours_end: '08:00',
  quiet_hours_allow_critical: false,
  grouping_enabled: true,
  grouping_window_seconds: 300,
  sound_enabled: true,
  vibration_enabled: true,
  badge_enabled: true,
  retention_days: 30,
})

async function loadPreferences() {
  loading.value = true
  error.value = ''
  try {
    const res = await api.get('/api/notifications/center/preferences')
    preferences.value = { ...preferences.value, ...res }
  } catch (e: any) {
    error.value = e.message || 'Failed to load preferences'
  } finally {
    loading.value = false
  }
}

async function savePreferences() {
  saving.value = true
  error.value = ''
  try {
    await api.put('/api/notifications/center/preferences', preferences.value)
  } catch (e: any) {
    error.value = e.message || 'Failed to save preferences'
  } finally {
    saving.value = false
  }
}

function handleClose() {
  emit('close')
}

onMounted(() => {
  loadPreferences()
})

// Auto-save on changes
watch(preferences, () => {
  savePreferences()
}, { deep: true })
</script>

<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div 
        class="w-full max-w-lg mx-4 bg-surface rounded-xl border border-border/40 shadow-2xl overflow-hidden"
        @click.stop
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-5 py-4 border-b border-border/20">
          <div>
            <h2 class="text-sm font-semibold text-foreground">Notification Settings</h2>
            <p class="text-[10px] text-muted-foreground mt-0.5">Configure how you receive notifications</p>
          </div>
          <button
            @click="handleClose"
            class="flex items-center justify-center rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-surface/50 transition-colors"
          >
            <X class="h-4 w-4" />
          </button>
        </div>

        <!-- Content -->
        <div class="max-h-[60vh] overflow-y-auto px-5 py-4 space-y-6">
          <!-- Loading State -->
          <div v-if="loading" class="py-8 text-center">
            <div class="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full mx-auto" />
            <p class="mt-3 text-xs text-muted-foreground">Loading settings...</p>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="py-4 text-center">
            <p class="text-xs text-destructive">{{ error }}</p>
            <button 
              @click="loadPreferences" 
              class="mt-2 text-[10px] text-primary hover:underline"
            >
              Retry
            </button>
          </div>

          <!-- Settings Form -->
          <template v-else>
            <!-- Channels -->
            <div class="space-y-3">
              <h3 class="text-xs font-semibold text-foreground uppercase tracking-wider">Channels</h3>
              
              <label class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Desktop notifications</p>
                  <p class="text-[10px] text-muted-foreground">System tray notifications</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.desktop_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <label class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Mobile push</p>
                  <p class="text-[10px] text-muted-foreground">Push notifications to your phone</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.mobile_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <label class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Watch notifications</p>
                  <p class="text-[10px] text-muted-foreground">High-priority alerts on your watch</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.watch_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <label class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Email (monthly report only)</p>
                  <p class="text-[10px] text-muted-foreground">Receive monthly summary via email</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.email_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>
            </div>

            <!-- Priorities -->
            <div class="space-y-3">
              <h3 class="text-xs font-semibold text-foreground uppercase tracking-wider">Priority Levels</h3>
              
              <label class="flex items-center justify-between py-2">
                <div class="flex items-center gap-2">
                  <div class="h-2 w-2 rounded-full bg-destructive" />
                  <p class="text-xs text-foreground">Critical</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.critical_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <label class="flex items-center justify-between py-2">
                <div class="flex items-center gap-2">
                  <div class="h-2 w-2 rounded-full bg-warning" />
                  <p class="text-xs text-foreground">High</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.high_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <label class="flex items-center justify-between py-2">
                <div class="flex items-center gap-2">
                  <div class="h-2 w-2 rounded-full bg-primary" />
                  <p class="text-xs text-foreground">Medium</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.medium_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <label class="flex items-center justify-between py-2">
                <div class="flex items-center gap-2">
                  <div class="h-2 w-2 rounded-full bg-muted-foreground" />
                  <p class="text-xs text-foreground">Low</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.low_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <label class="flex items-center justify-between py-2">
                <div class="flex items-center gap-2">
                  <div class="h-2 w-2 rounded-full bg-info" />
                  <p class="text-xs text-foreground">Info</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.info_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>
            </div>

            <!-- Features -->
            <div class="space-y-3">
              <h3 class="text-xs font-semibold text-foreground uppercase tracking-wider">Features</h3>
              
              <label class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Daily briefing</p>
                  <p class="text-[10px] text-muted-foreground">"Next Best Action" notification</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.daily_briefing_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <label class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Monthly report</p>
                  <p class="text-[10px] text-muted-foreground">Email summary of the month</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.monthly_report_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <div v-if="preferences.monthly_report_enabled" class="ml-4 mt-2">
                <label class="block text-[10px] text-muted-foreground mb-1">Monthly report email</label>
                <input
                  v-model="preferences.monthly_report_email"
                  type="email"
                  placeholder="your@email.com"
                  class="w-full px-3 py-1.5 text-xs bg-background border border-border/40 rounded-lg focus:outline-none focus:border-primary/60"
                />
              </div>
            </div>

            <!-- Quiet Hours -->
            <div class="space-y-3">
              <h3 class="text-xs font-semibold text-foreground uppercase tracking-wider">Quiet Hours</h3>
              
              <label class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Enable quiet hours</p>
                  <p class="text-[10px] text-muted-foreground">Suppress non-critical notifications</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.quiet_hours_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <div v-if="preferences.quiet_hours_enabled" class="ml-4 mt-2 space-y-2">
                <div class="flex gap-4">
                  <div>
                    <label class="block text-[10px] text-muted-foreground mb-1">Start</label>
                    <input
                      v-model="preferences.quiet_hours_start"
                      type="time"
                      class="px-3 py-1.5 text-xs bg-background border border-border/40 rounded-lg focus:outline-none focus:border-primary/60"
                    />
                  </div>
                  <div>
                    <label class="block text-[10px] text-muted-foreground mb-1">End</label>
                    <input
                      v-model="preferences.quiet_hours_end"
                      type="time"
                      class="px-3 py-1.5 text-xs bg-background border border-border/40 rounded-lg focus:outline-none focus:border-primary/60"
                    />
                  </div>
                </div>
                
                <label class="flex items-center gap-2 py-1">
                  <input
                    type="checkbox"
                    v-model="preferences.quiet_hours_allow_critical"
                    class="rounded border-border"
                  />
                  <span class="text-[10px] text-muted-foreground">Allow CRITICAL during quiet hours</span>
                </label>
              </div>
            </div>

            <!-- Other -->
            <div class="space-y-3">
              <h3 class="text-xs font-semibold text-foreground uppercase tracking-wider">Other</h3>
              
              <label class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Sound</p>
                  <p class="text-[10px] text-muted-foreground">Play sound for notifications</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.sound_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <label class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Grouping</p>
                  <p class="text-[10px] text-muted-foreground">Group related notifications</p>
                </div>
                <div class="relative">
                  <input 
                    type="checkbox" 
                    v-model="preferences.grouping_enabled"
                    class="sr-only peer"
                  />
                  <div class="w-9 h-5 bg-muted rounded-full peer peer-checked:bg-primary transition-colors" />
                  <div class="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full peer-checked:translate-x-4 transition-transform" />
                </div>
              </label>

              <div v-if="preferences.grouping_enabled" class="ml-4 mt-2">
                <label class="block text-[10px] text-muted-foreground mb-1">Grouping window (seconds)</label>
                <input
                  v-model.number="preferences.grouping_window_seconds"
                  type="number"
                  min="60"
                  max="3600"
                  class="w-24 px-3 py-1.5 text-xs bg-background border border-border/40 rounded-lg focus:outline-none focus:border-primary/60"
                />
              </div>

              <div class="flex items-center justify-between py-2">
                <div>
                  <p class="text-xs text-foreground">Retention</p>
                  <p class="text-[10px] text-muted-foreground">Keep notifications for</p>
                </div>
                <div class="flex items-center gap-2">
                  <input
                    v-model.number="preferences.retention_days"
                    type="number"
                    min="7"
                    max="365"
                    class="w-16 px-2 py-1 text-xs bg-background border border-border/40 rounded-lg focus:outline-none focus:border-primary/60 text-right"
                  />
                  <span class="text-[10px] text-muted-foreground">days</span>
                </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Footer -->
        <div class="px-5 py-3 border-t border-border/20 flex items-center justify-between">
          <p v-if="saving" class="text-[10px] text-muted-foreground">Saving...</p>
          <p v-else-if="error" class="text-[10px] text-destructive">{{ error }}</p>
          <p v-else class="text-[10px] text-success">Settings saved</p>
          
          <button
            @click="handleClose"
            class="px-4 py-1.5 text-xs font-medium bg-primary text-background rounded-lg hover:opacity-90 transition-opacity"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
