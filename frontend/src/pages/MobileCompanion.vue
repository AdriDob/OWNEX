<template>
  <div class="auth-wrapper">
    <!-- Login Screen -->
    <div v-if="authState === 'login'" class="auth-screen">
      <div class="auth-container">
        <div class="auth-header">
          <div class="logo">🤖 ORION</div>
          <div class="subtitle">Cloud Sync Powered by Supabase</div>
        </div>

        <form @submit.prevent="handleLogin" class="auth-form">
          <div class="form-group">
            <label>Email</label>
            <input
              v-model="loginForm.email"
              type="email"
              placeholder="your@email.com"
              class="form-input"
              required
            />
          </div>

          <div class="form-group">
            <label>Password</label>
            <input
              v-model="loginForm.password"
              type="password"
              placeholder="••••••••"
              class="form-input"
              required
            />
          </div>

          <button type="submit" class="auth-btn" :disabled="loading">
            {{ loading ? 'Logging in...' : 'Login' }}
          </button>

          <div class="auth-footer">
            <span>Don't have an account?</span>
            <button @click="authState = 'register'" class="link-btn">Register</button>
          </div>
        </form>

        <div v-if="error" class="error-message">{{ error }}</div>
      </div>
    </div>

    <!-- Register Screen -->
    <div v-if="authState === 'register'" class="auth-screen">
      <div class="auth-container">
        <div class="auth-header">
          <div class="logo">🤖 ORION</div>
          <div class="subtitle">Create Account</div>
        </div>

        <form @submit.prevent="handleRegister" class="auth-form">
          <div class="form-group">
            <label>Email</label>
            <input
              v-model="registerForm.email"
              type="email"
              placeholder="your@email.com"
              class="form-input"
              required
            />
          </div>

          <div class="form-group">
            <label>Password</label>
            <input
              v-model="registerForm.password"
              type="password"
              placeholder="••••••••"
              class="form-input"
              required
              minlength="6"
            />
          </div>

          <div class="form-group">
            <label>Confirm Password</label>
            <input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="••••••••"
              class="form-input"
              required
              minlength="6"
            />
          </div>

          <button type="submit" class="auth-btn" :disabled="loading">
            {{ loading ? 'Creating account...' : 'Register' }}
          </button>

          <div class="auth-footer">
            <span>Already have an account?</span>
            <button @click="authState = 'login'" class="link-btn">Login</button>
          </div>
        </form>

        <div v-if="error" class="error-message">{{ error }}</div>
      </div>
    </div>

    <!-- Main App (after login) -->
    <div v-if="authState === 'authenticated'" class="mobile-companion-wrapper">
      <!-- Header -->
      <div class="mobile-header">
        <div class="header-content">
          <div class="logo">🤖 ORION</div>
          <div class="status-indicator" :class="syncStatus">
            <div class="status-dot"></div>
            <span>{{ syncStatusText }}</span>
          </div>
        </div>
        <div class="header-actions">
          <button @click="refreshData" class="icon-btn" title="Refresh">
            <RefreshCw :class="{ spinning: refreshing }" />
          </button>
          <button @click="showSettings = true" class="icon-btn" title="Settings">
            ⚙️
          </button>
          <button @click="handleLogout" class="icon-btn" title="Logout">
            🚪
          </button>
        </div>
      </div>

      <!-- Dashboard -->
      <div class="dashboard">
        <!-- System Health Card -->
        <div class="card health-card">
          <div class="card-header">
            <h3>📊 System Health</h3>
            <Badge :variant="healthVariant">{{ healthScore }}/100</Badge>
          </div>
          <div class="health-metrics">
            <div class="metric">
              <div class="metric-label">Backend</div>
              <div class="metric-value" :class="backendStatus">{{ backendStatusText }}</div>
            </div>
            <div class="metric">
              <div class="metric-label">Supabase</div>
              <div class="metric-value" :class="supabaseStatus">{{ supabaseStatusText }}</div>
            </div>
            <div class="metric">
              <div class="metric-label">Sync</div>
              <div class="metric-value" :class="syncStatus">{{ syncStatusText }}</div>
            </div>
          </div>
        </div>

        <!-- Tasks Card -->
        <div class="card tasks-card">
          <div class="card-header">
            <h3>📋 Tasks</h3>
            <Badge>{{ tasks.length }}</Badge>
          </div>
          <div class="tasks-list">
            <div v-for="task in tasks" :key="task.task_id" class="task-item" :class="{ completed: task.status === 'completed' }">
              <div class="task-info">
                <div class="task-title">{{ task.title }}</div>
                <div class="task-status" :class="task.status">{{ task.status }}</div>
              </div>
              <button @click="toggleTask(task)" class="icon-btn-small">✓</button>
            </div>
          </div>
          <button @click="showAddTask = true" class="add-btn">+ Add Task</button>
        </div>

        <!-- Goals Card -->
        <div class="card goals-card">
          <div class="card-header">
            <h3>🎯 Goals</h3>
            <Badge>{{ goals.length }}</Badge>
          </div>
          <div class="goals-list">
            <div v-for="goal in goals" :key="goal.goal_id" class="goal-item">
              <div class="goal-info">
                <div class="goal-title">{{ goal.title }}</div>
                <div class="goal-progress">
                  <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: goal.progress + '%' }"></div>
                  </div>
                  <span class="progress-text">{{ goal.progress }}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Habits Card -->
        <div class="card habits-card">
          <div class="card-header">
            <h3>🔄 Habits</h3>
            <Badge>{{ habits.length }}</Badge>
          </div>
          <div class="habits-list">
            <div v-for="habit in habits" :key="habit.habit_id" class="habit-item">
              <div class="habit-info">
                <div class="habit-title">{{ habit.title }}</div>
                <div class="habit-streak">🔥 {{ habit.streak }} day streak</div>
              </div>
              <button @click="completeHabit(habit)" class="icon-btn-small">✓</button>
            </div>
          </div>
        </div>

        <!-- Daily Mood Card -->
        <div class="card mood-card">
          <div class="card-header">
            <h3>😊 Daily Mood</h3>
            <Badge :variant="moodVariant">{{ currentMood }}</Badge>
          </div>
          <div class="mood-selector">
            <button
              v-for="mood in moods"
              :key="mood.value"
              @click="setMood(mood.value)"
              class="mood-btn"
              :class="{ active: currentMood === mood.value }"
            >
              {{ mood.emoji }}
            </button>
          </div>
          <div class="mood-metrics">
            <div class="mood-metric">
              <label>Energy</label>
              <input v-model.number="moodData.energy_level" type="range" min="1" max="10" class="range-input" />
              <span>{{ moodData.energy_level }}/10</span>
            </div>
            <div class="mood-metric">
              <label>Stress</label>
              <input v-model.number="moodData.stress_level" type="range" min="1" max="10" class="range-input" />
              <span>{{ moodData.stress_level }}/10</span>
            </div>
          </div>
          <button @click="saveMood" class="save-btn">Save Mood</button>
        </div>
      </div>

      <!-- Add Task Modal -->
      <div v-if="showAddTask" class="modal-overlay" @click="showAddTask = false">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>Add Task</h3>
            <button @click="showAddTask = false" class="close-btn">✕</button>
          </div>
          <div class="modal-body">
            <div class="form-group">
              <label>Title</label>
              <input v-model="newTask.title" type="text" class="form-input" placeholder="Task title" />
            </div>
            <div class="form-group">
              <label>Priority</label>
              <select v-model="newTask.priority" class="form-input">
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div class="form-group">
              <label>Category</label>
              <select v-model="newTask.category" class="form-input">
                <option value="work">Work</option>
                <option value="personal">Personal</option>
                <option value="health">Health</option>
                <option value="finance">Finance</option>
                <option value="learning">Learning</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="addTask" class="btn-primary">Add Task</button>
          </div>
        </div>
      </div>

      <!-- Settings Modal -->
      <div v-if="showSettings" class="modal-overlay" @click="showSettings = false">
        <div class="modal-content" @click.stop>
          <div class="modal-header">
            <h3>⚙️ Settings</h3>
            <button @click="showSettings = false" class="close-btn">✕</button>
          </div>
          <div class="settings-content">
            <div class="setting-item">
              <label>Push Notifications</label>
              <input type="checkbox" v-model="settings.pushEnabled" class="toggle" />
            </div>
            <div class="setting-item">
              <label>Auto-sync</label>
              <input type="checkbox" v-model="settings.autoSync" class="toggle" />
            </div>
            <div class="setting-item">
              <label>Sync Interval (min)</label>
              <input type="number" v-model="settings.syncInterval" class="number-input" />
            </div>
          </div>
          <div class="modal-footer">
            <button @click="saveSettings" class="btn-primary">Save</button>
          </div>
        </div>
      </div>

      <!-- Navigation Bar -->
      <div class="nav-bar">
        <button @click="activeTab = 'dashboard'" class="nav-item" :class="{ active: activeTab === 'dashboard' }">
          📊
        </button>
        <button @click="activeTab = 'tasks'" class="nav-item" :class="{ active: activeTab === 'tasks' }">
          📋
        </button>
        <button @click="activeTab = 'goals'" class="nav-item" :class="{ active: activeTab === 'goals' }">
          🎯
        </button>
        <button @click="activeTab = 'habits'" class="nav-item" :class="{ active: activeTab === 'habits' }">
          🔄
        </button>
        <button @click="activeTab = 'mood'" class="nav-item" :class="{ active: activeTab === 'mood' }">
          😊
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RefreshCw } from '@lucide/vue'
import Badge from '@/components/ui/Badge.vue'

// State
const authState = ref<'login' | 'register' | 'authenticated'>('login')
const loading = ref(false)
const error = ref('')

// Login form
const loginForm = ref({
  email: '',
  password: '',
})

// Register form
const registerForm = ref({
  email: '',
  password: '',
  confirmPassword: '',
})

// Supabase client
let supabase: any = null
let userId: string = ''

// App state
const syncStatus = ref('synced')
const healthScore = ref(85)
const backendStatus = ref('online')
const supabaseStatus = ref('connected')
const refreshing = ref(false)
const showSettings = ref(false)
const showAddTask = ref(false)
const activeTab = ref('dashboard')

// Data
const tasks = ref<any[]>([])
const goals = ref<any[]>([])
const habits = ref<any[]>([])
const currentMood = ref('neutral')

// Mood data
const moodData = ref({
  mood: 'neutral',
  energy_level: 5,
  stress_level: 5,
})

const moods = [
  { value: 'very_positive', emoji: '😄' },
  { value: 'positive', emoji: '🙂' },
  { value: 'neutral', emoji: '😐' },
  { value: 'negative', emoji: '😔' },
  { value: 'very_negative', emoji: '😢' },
]

// New task
const newTask = ref({
  title: '',
  priority: 'medium',
  category: 'work',
})

// Settings
const settings = ref({
  pushEnabled: true,
  autoSync: true,
  syncInterval: 5,
})

// Computed
const syncStatusText = computed(() => {
  const status = syncStatus.value
  return status === 'synced' ? 'Synced' : status === 'syncing' ? 'Syncing...' : 'Offline'
})

const healthVariant = computed(() => {
  if (healthScore.value >= 80) return 'success'
  if (healthScore.value >= 50) return 'warning'
  return 'danger'
})

const backendStatusText = computed(() => backendStatus.value === 'online' ? 'Online' : 'Offline')
const supabaseStatusText = computed(() => supabaseStatus.value === 'connected' ? 'Connected' : 'Disconnected')

const moodVariant = computed(() => {
  const mood = currentMood.value
  if (mood === 'very_positive' || mood === 'positive') return 'success'
  if (mood === 'neutral') return 'outline'
  return 'danger'
})

// Methods
const initSupabase = async () => {
  try {
    const { createClient } = await import('@supabase/supabase-js')

    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
    const supabaseKey = import.meta.env.VITE_SUPABASE_KEY

    if (!supabaseUrl || !supabaseKey) {
      throw new Error('Supabase credentials not configured')
    }

    supabase = createClient(supabaseUrl, supabaseKey)
    console.log('Supabase initialized')
  } catch (e) {
    console.error('Failed to initialize Supabase:', e)
    error.value = 'Failed to initialize Supabase'
  }
}

const handleLogin = async () => {
  loading.value = true
  error.value = ''

  try {
    const { data, error: authError } = await supabase.auth.signInWithPassword({
      email: loginForm.value.email,
      password: loginForm.value.password,
    })

    if (authError) throw authError

    userId = data.user.id
    authState.value = 'authenticated'

    // Load data
    await loadAllData()
  } catch (e: any) {
    error.value = e.message || 'Login failed'
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  loading.value = true
  error.value = ''

  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    error.value = 'Passwords do not match'
    loading.value = false
    return
  }

  try {
    const { data, error: authError } = await supabase.auth.signUp({
      email: registerForm.value.email,
      password: registerForm.value.password,
    })

    if (authError) throw authError

    userId = data.user.id
    authState.value = 'authenticated'

    // Load data
    await loadAllData()
  } catch (e: any) {
    error.value = e.message || 'Registration failed'
  } finally {
    loading.value = false
  }
}

const handleLogout = async () => {
  await supabase.auth.signOut()
  authState.value = 'login'
  userId = ''
  tasks.value = []
  goals.value = []
  habits.value = []
}

const loadAllData = async () => {
  syncStatus.value = 'syncing'

  try {
    // Load tasks
    const { data: tasksData } = await supabase
      .from('tasks')
      .select('*')
      .eq('user_id', userId)

    tasks.value = tasksData || []

    // Load goals
    const { data: goalsData } = await supabase
      .from('goals')
      .select('*')
      .eq('user_id', userId)

    goals.value = goalsData || []

    // Load habits
    const { data: habitsData } = await supabase
      .from('habits')
      .select('*')
      .eq('user_id', userId)

    habits.value = habitsData || []

    // Load today's mood
    const today = new Date().toISOString().split('T')[0]
    const { data: moodData: todayMood } = await supabase
      .from('daily_moods')
      .select('*')
      .eq('user_id', userId)
      .eq('date', today)
      .single()

    if (todayMood) {
      currentMood.value = todayMood.mood
      moodData.value = {
        mood: todayMood.mood,
        energy_level: todayMood.energy_level || 5,
        stress_level: todayMood.stress_level || 5,
      }
    }

    syncStatus.value = 'synced'
  } catch (e) {
    console.error('Failed to load data:', e)
    syncStatus.value = 'offline'
  }
}

const refreshData = async () => {
  refreshing.value = true
  await loadAllData()
  refreshing.value = false
}

const toggleTask = async (task: any) => {
  const newStatus = task.status === 'completed' ? 'pending' : 'completed'

  const { error } = await supabase
    .from('tasks')
    .update({ status: newStatus, completed_at: newStatus === 'completed' ? new Date().toISOString() : null })
    .eq('task_id', task.task_id)

  if (!error) {
    task.status = newStatus
  }
}

const addTask = async () => {
  const taskData = {
    user_id: userId,
    task_id: `task-${Date.now()}`,
    title: newTask.value.title,
    status: 'pending',
    priority: newTask.value.priority,
    category: newTask.value.category,
    created_at: new Date().toISOString(),
  }

  const { error } = await supabase.from('tasks').insert(taskData)

  if (!error) {
    tasks.value.push(taskData)
    showAddTask.value = false
    newTask.value = { title: '', priority: 'medium', category: 'work' }
  }
}

const completeHabit = async (habit: any) => {
  const entryData = {
    user_id: userId,
    habit_id: habit.habit_id,
    date: new Date().toISOString().split('T')[0],
    completed: true,
    energy_level: 5,
  }

  const { error } = await supabase.from('habit_entries').insert(entryData)

  if (!error) {
    habit.streak += 1
  }
}

const setMood = (mood: string) => {
  currentMood.value = mood
  moodData.value.mood = mood
}

const saveMood = async () => {
  const today = new Date().toISOString().split('T')[0]

  const moodDataToSave = {
    user_id: userId,
    date: today,
    mood: moodData.value.mood,
    energy_level: moodData.value.energy_level,
    stress_level: moodData.value.stress_level,
  }

  const { error } = await supabase
    .from('daily_moods')
    .upsert(moodDataToSave)

  if (!error) {
    console.log('Mood saved')
  }
}

const saveSettings = () => {
  localStorage.setItem('mobileSettings', JSON.stringify(settings.value))
  showSettings.value = false
}

// Lifecycle
onMounted(async () => {
  await initSupabase()

  // Check for existing session
  const { data: { session } } = await supabase.auth.getSession()

  if (session) {
    userId = session.user.id
    authState.value = 'authenticated'
    await loadAllData()
  }

  // Load settings
  const savedSettings = localStorage.getItem('mobileSettings')
  if (savedSettings) {
    settings.value = JSON.parse(savedSettings)
  }

  // Auto-sync
  if (settings.value.autoSync) {
    setInterval(loadAllData, settings.value.syncInterval * 60000)
  }
})

onUnmounted(() => {
  // Cleanup
})
</script>

<style scoped>
.auth-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 100%);
  color: #fff;
  font-family: 'Inter', sans-serif;
}

.auth-screen {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  padding: 20px;
}

.auth-container {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 16px;
  padding: 40px;
  max-width: 400px;
  width: 100%;
  backdrop-filter: blur(10px);
}

.auth-header {
  text-align: center;
  margin-bottom: 30px;
}

.logo {
  font-size: 2rem;
  font-weight: bold;
  color: #00f0ff;
  margin-bottom: 10px;
}

.subtitle {
  color: #888;
  font-size: 0.9rem;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  color: #fff;
  font-size: 0.9rem;
}

.form-input {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 8px;
  color: #fff;
  padding: 12px;
  font-family: 'Inter', sans-serif;
}

.auth-btn {
  background: #00f0ff;
  color: #000;
  border: none;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  font-size: 1rem;
}

.auth-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.auth-footer {
  text-align: center;
  color: #888;
  font-size: 0.9rem;
}

.link-btn {
  background: none;
  border: none;
  color: #00f0ff;
  cursor: pointer;
  font-weight: bold;
}

.error-message {
  color: #ff6b35;
  text-align: center;
  margin-top: 20px;
}

.mobile-companion-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 100%);
  color: #fff;
  font-family: 'Inter', sans-serif;
  padding-bottom: 80px;
}

.mobile-header {
  background: rgba(0, 240, 255, 0.1);
  border-bottom: 1px solid rgba(0, 240, 255, 0.3);
  padding: 15px 20px;
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
}

.status-indicator.synced .status-dot {
  background: #00ff88;
}

.status-indicator.syncing .status-dot {
  background: #ffaa00;
  animation: pulse 1s infinite;
}

.status-indicator.offline .status-dot {
  background: #ff6b35;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #00ff88;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.header-actions {
  display: flex;
  gap: 10px;
}

.icon-btn {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  color: #00f0ff;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.icon-btn.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.dashboard {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 16px;
  padding: 20px;
  backdrop-filter: blur(10px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.card-header h3 {
  margin: 0;
  color: #00f0ff;
  font-size: 1.1rem;
}

.health-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
}

.metric {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.1);
  border-radius: 12px;
  padding: 12px;
}

.metric-label {
  color: #888;
  font-size: 0.85rem;
  margin-bottom: 5px;
}

.metric-value {
  color: #fff;
  font-weight: bold;
  font-size: 1rem;
}

.metric-value.online,
.metric-value.connected,
.metric-value.synced {
  color: #00ff88;
}

.metric-value.offline,
.metric-value.disconnected {
  color: #ff6b35;
}

.tasks-list,
.goals-list,
.habits-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-item,
.goal-item,
.habit-item {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.1);
  border-radius: 12px;
  padding: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-item.completed {
  opacity: 0.5;
}

.task-title,
.goal-title,
.habit-title {
  color: #fff;
  font-weight: 600;
  margin-bottom: 5px;
}

.task-status {
  font-size: 0.8rem;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
}

.task-status.completed {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
}

.task-status.pending {
  background: rgba(255, 170, 0, 0.2);
  color: #ffaa00;
}

.goal-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.progress-bar {
  flex: 1;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  height: 6px;
  overflow: hidden;
}

.progress-fill {
  background: linear-gradient(90deg, #00f0ff, #00ff88);
  height: 100%;
  border-radius: 10px;
  transition: width 0.3s ease;
}

.progress-text {
  color: #00f0ff;
  font-size: 0.85rem;
  font-weight: bold;
}

.habit-streak {
  color: #ffaa00;
  font-size: 0.8rem;
}

.icon-btn-small {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid rgba(0, 255, 136, 0.3);
  color: #00ff88;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.add-btn {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  color: #00f0ff;
  padding: 10px;
  border-radius: 8px;
  cursor: pointer;
  width: 100%;
  margin-top: 10px;
}

.mood-selector {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;
}

.mood-btn {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 8px;
  padding: 10px 15px;
  cursor: pointer;
  font-size: 1.5rem;
  transition: all 0.3s ease;
}

.mood-btn.active {
  background: rgba(0, 240, 255, 0.2);
  border-color: #00f0ff;
  transform: scale(1.1);
}

.mood-metrics {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.mood-metric {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mood-metric label {
  color: #888;
  font-size: 0.9rem;
  min-width: 60px;
}

.range-input {
  flex: 1;
}

.save-btn {
  background: #00f0ff;
  color: #000;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
  width: 100%;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 1px solid #00f0ff;
  border-radius: 16px;
  padding: 30px;
  max-width: 400px;
  width: 90%;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.modal-header h3 {
  margin: 0;
  color: #00f0ff;
}

.close-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setting-item label {
  color: #fff;
  font-size: 0.95rem;
}

.toggle,
.number-input {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 8px;
  color: #fff;
  padding: 8px 12px;
}

.number-input {
  width: 80px;
}

.btn-primary {
  background: #00f0ff;
  color: #000;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: bold;
}

.nav-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.9);
  border-top: 1px solid rgba(0, 240, 255, 0.3);
  display: flex;
  justify-content: space-around;
  padding: 10px 0;
  backdrop-filter: blur(10px);
}

.nav-item {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.2);
  color: #00f0ff;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1.5rem;
  transition: all 0.3s ease;
}

.nav-item.active {
  background: #00f0ff;
  color: #000;
  transform: scale(1.1);
}
</style>
