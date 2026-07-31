<template>
  <div class="life-management-container">
    <!-- Header -->
    <div class="header">
      <h1>🧘 Life Management</h1>
      <p class="subtitle">Gestión de vida personal — Tareas, Metas, Hábitos y Más</p>
      <div class="date-selector">
        <input type="date" v-model="selectedDate" @change="loadDayData" />
      </div>
    </div>

    <!-- Daily Summary Card -->
    <div class="daily-summary-card">
      <h2>📊 Resumen del Día</h2>
      <div class="summary-grid">
        <div class="summary-item">
          <div class="summary-label">Tareas</div>
          <div class="summary-value">{{ summary.tasks_completed }}/{{ summary.tasks_total }}</div>
          <div class="summary-bar">
            <div class="summary-progress" :style="{ width: (summary.tasks_completed / summary.tasks_total * 100) + '%' }"></div>
          </div>
        </div>
        <div class="summary-item">
          <div class="summary-label">Hábitos</div>
          <div class="summary-value">{{ summary.habits_completed }}/{{ summary.habits_total }}</div>
          <div class="summary-bar">
            <div class="summary-progress" :style="{ width: (summary.habits_completion_rate * 100) + '%' }"></div>
          </div>
        </div>
        <div class="summary-item">
          <div class="summary-label">Metas</div>
          <div class="summary-value">{{ summary.goals_total_progress }}%</div>
          <div class="summary-bar">
            <div class="summary-progress" :style="{ width: summary.goals_total_progress + '%' }"></div>
          </div>
        </div>
        <div class="summary-item">
          <div class="summary-label">PC Usage</div>
          <div class="summary-value">{{ Math.round(summary.pc_usage.total_minutes / 60) }}h</div>
          <div class="summary-bar">
            <div class="summary-progress" :style="{ width: (summary.pc_usage.productive_minutes / summary.pc_usage.total_minutes * 100) + '%' }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="main-grid">
      <!-- Tasks Section -->
      <div class="section-card tasks-section">
        <div class="section-header">
          <h2>📋 Tareas</h2>
          <button @click="showTaskModal = true" class="btn-primary">+ Nueva Tarea</button>
        </div>
        <div class="filter-tabs">
          <button :class="{ active: taskFilter === 'all' }" @click="taskFilter = 'all'">Todas</button>
          <button :class="{ active: taskFilter === 'work' }" @click="taskFilter = 'work'">Trabajo</button>
          <button :class="{ active: taskFilter === 'personal' }" @click="taskFilter = 'personal'">Personal</button>
          <button :class="{ active: taskFilter === 'health' }" @click="taskFilter = 'health'">Salud</button>
        </div>
        <div class="tasks-list">
          <div v-for="task in filteredTasks" :key="task.task_id" class="task-item" :class="task.status">
            <div class="task-priority" :class="task.priority"></div>
            <div class="task-content">
              <div class="task-title">{{ task.title }}</div>
              <div class="task-meta">
                <span v-if="task.due_date" class="task-due">📅 {{ formatDate(task.due_date) }}</span>
                <span class="task-time">⏱️ {{ task.estimated_minutes }}min</span>
              </div>
            </div>
            <div class="task-actions">
              <button @click="completeTask(task.task_id)" class="btn-complete" title="Completar">✓</button>
              <button @click="deleteTask(task.task_id)" class="btn-delete" title="Eliminar">🗑️</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Goals Section -->
      <div class="section-card goals-section">
        <div class="section-header">
          <h2>🎯 Metas a Largo Plazo</h2>
          <button @click="showGoalModal = true" class="btn-primary">+ Nueva Meta</button>
        </div>
        <div class="goals-list">
          <div v-for="goal in goals" :key="goal.goal_id" class="goal-item" :class="goal.status">
            <div class="goal-category" :class="goal.category">{{ goal.category }}</div>
            <div class="goal-content">
              <div class="goal-title">{{ goal.title }}</div>
              <div class="goal-meta">
                <span class="goal-date">📅 {{ formatDate(goal.target_date) }}</span>
                <span class="goal-progress">{{ goal.progress_percentage }}%</span>
              </div>
              <div class="goal-progress-bar">
                <div class="goal-progress-fill" :style="{ width: goal.progress_percentage + '%' }"></div>
              </div>
            </div>
            <div class="goal-actions">
              <button @click="updateGoalProgress(goal.goal_id)" class="btn-progress" title="Actualizar Progreso">📊</button>
              <button @click="deleteGoal(goal.goal_id)" class="btn-delete" title="Eliminar">🗑️</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Habits Section -->
      <div class="section-card habits-section">
        <div class="section-header">
          <h2>🔄 Hábitos Diarios</h2>
          <button @click="showHabitModal = true" class="btn-primary">+ Nuevo Hábito</button>
        </div>
        <div class="habits-list">
          <div v-for="habit in habits" :key="habit.habit_id" class="habit-item" :class="habit.status">
            <div class="habit-icon">🔄</div>
            <div class="habit-content">
              <div class="habit-title">{{ habit.title }}</div>
              <div class="habit-meta">
                <span class="habit-streak">🔥 {{ habit.streak_days }} días</span>
                <span class="habit-frequency">{{ habit.frequency }}</span>
              </div>
            </div>
            <div class="habit-actions">
              <button @click="logHabitEntry(habit.habit_id)" class="btn-log" title="Registrar Hoy">✓</button>
              <button @click="deleteHabit(habit.habit_id)" class="btn-delete" title="Eliminar">🗑️</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Mood Tracking Section -->
      <div class="section-card mood-section">
        <div class="section-header">
          <h2">😊 Estado de Ánimo</h2>
        </div>
        <div class="mood-input">
          <label>Estado de ánimo actual:</label>
          <div class="mood-selector">
            <button @click="currentMood = 'very_positive'" :class="{ active: currentMood === 'very_positive' }">😄</button>
            <button @click="currentMood = 'positive'" :class="{ active: currentMood === 'positive' }">🙂</button>
            <button @click="currentMood = 'neutral'" :class="{ active: currentMood === 'neutral' }">😐</button>
            <button @click="currentMood = 'negative'" :class="{ active: currentMood === 'negative' }">😔</button>
            <button @click="currentMood = 'very_negative'" :class="{ active: currentMood === 'very_negative' }">😢</button>
          </div>
        </div>
        <div class="energy-input">
          <label>Nivel de Energía (1-10):</label>
          <input type="range" v-model="energyLevel" min="1" max="10" class="energy-slider" />
          <span class="energy-value">{{ energyLevel }}</span>
        </div>
        <div class="stress-input">
          <label>Nivel de Estrés (1-10):</label>
          <input type="range" v-model="stressLevel" min="1" max="10" class="stress-slider" />
          <span class="stress-value">{{ stressLevel }}</span>
        </div>
        <div class="notes-input">
          <label>Notas del día:</label>
          <textarea v-model="dailyNotes" placeholder="¿Qué pasó hoy? ¿Qué aprendiste?" class="notes-textarea"></textarea>
        </div>
        <button @click="saveDailyMood" class="btn-save">Guardar Estado de Ánimo</button>
      </div>

      <!-- Advice Section -->
      <div class="section-card advice-section">
        <div class="section-header">
          <h2>💡 Consejos Personalizados</h2>
          <button @click="generateAdvice" class="btn-secondary">Generar Nuevo Consejo</button>
        </div>
        <div class="advice-list">
          <div v-for="advice in advices" :key="advice.advice_id" class="advice-item">
            <div class="advice-category">{{ advice.category }}</div>
            <div class="advice-title">{{ advice.title }}</div>
            <div class="advice-content">{{ advice.content }}</div>
            <div class="advice-actions">
              <button @click="markAdviceHelpful(advice.advice_id)" class="btn-helpful">👍 Helpful</button>
              <button @click="dismissAdvice(advice.advice_id)" class="btn-dismiss">✕️</button>
            </div>
          </div>
        </div>
      </div>

      <!-- PC Usage Section -->
      <div class="section-card pc-usage-section">
        <div class="section-header">
          <h2>💻 Uso de PC</h2>
          <button @click="startPCSession" class="btn-primary" v-if="!activeSession">Iniciar Sesión</button>
          <button @click="endPCSession" class="btn-danger" v-else>Finalizar Sesión</button>
        </div>
        <div v-if="activeSession" class="active-session-info">
          <div class="session-info">
            <span>⏱️ Sesión activa: {{ getSessionDuration() }} min</span>
            <span>📊 Productividad: {{ sessionProductivity }}/10</span>
          </div>
        </div>
        <div class="pc-usage-stats">
          <div class="stat-item">
            <div class="stat-label">Tiempo Total Hoy</div>
            <div class="stat-value">{{ Math.round(pcUsage.total_minutes / 60) }}h</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">Productivo</div>
            <div class="stat-value">{{ Math.round(pcUsage.productive_minutes / 60) }}h</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">Entretenimiento</div>
            <div class="stat-value">{{ Math.round((pcUsage.total_minutes - pcUsage.productive_minutes) / 60) }}h</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Task Modal -->
    <div v-if="showTaskModal" class="modal-overlay" @click="showTaskModal = false">
      <div class="modal-content" @click.stop>
        <h3>Nueva Tarea</h3>
        <form @submit.prevent="createTask">
          <div class="form-group">
            <label>Título:</label>
            <input v-model="newTask.title" required class="form-input" />
          </div>
          <div class="form-group">
            <label>Descripción:</label>
            <textarea v-model="newTask.description" class="form-textarea"></textarea>
          </div>
          <div class="form-group">
            <label>Categoría:</label>
            <select v-model="newTask.category" class="form-select">
              <option value="work">Trabajo</option>
              <option value="personal">Personal</option>
              <option value="health">Salud</option>
              <option value="finance">Finanzas</option>
              <option value="learning">Aprendizaje</option>
              <option value="social">Social</option>
              <option value="home">Hogar</option>
              <option value="hobby">Hobby</option>
            </select>
          </div>
          <div class="form-group">
            <label>Prioridad:</label>
            <select v-model="newTask.priority" class="form-select">
              <option value="critical">Crítica</option>
              <option value="high">Alta</option>
              <option value="medium">Media</option>
              <option value="low">Baja</option>
            </select>
          </div>
          <div class="form-group">
            <label>Fecha límite:</label>
            <input type="date" v-model="newTask.due_date" class="form-input" />
          </div>
          <div class="form-group">
            <label>Tiempo estimado (min):</label>
            <input type="number" v-model="newTask.estimated_minutes" class="form-input" />
          </div>
          <div class="form-actions">
            <button type="button" @click="showTaskModal = false" class="btn-cancel">Cancelar</button>
            <button type="submit" class="btn-primary">Crear Tarea</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Goal Modal -->
    <div v-if="showGoalModal" class="modal-overlay" @click="showGoalModal = false">
      <div class="modal-content" @click.stop>
        <h3>Nueva Meta</h3>
        <form @submit.prevent="createGoal">
          <div class="form-group">
            <label>Título:</label>
            <input v-model="newGoal.title" required class="form-input" />
          </div>
          <div class="form-group">
            <label>Descripción:</label>
            <textarea v-model="newGoal.description" class="form-textarea"></textarea>
          </div>
          <div class="form-group">
            <label>Categoría:</label>
            <select v-model="newGoal.category" class="form-select">
              <option value="career">Carrera</option>
              <option value="finance">Finanzas</option>
              <option value="health">Salud</option>
              <option value="relationships">Relaciones</option>
              <option value="personal_growth">Crecimiento Personal</option>
              <option value="skills">Habilidades</option>
              <option value="travel">Viajes</option>
              <option value="home">Hogar</option>
            </select>
          </div>
          <div class="form-group">
            <label>Fecha objetivo:</label>
            <input type="date" v-model="newGoal.target_date" required class="form-input" />
          </div>
          <div class="form-group">
            <label>Hitos (separados por coma):</label>
            <input v-model="newGoal.milestonesText" class="form-input" placeholder="Hito 1, Hito 2, Hito 3" />
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="newGoal.daily_focus" />
              Foco diario
            </label>
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="newGoal.vision_board" />
              Vision Board
            </label>
          </div>
          <div class="form-actions">
            <button type="button" @click="showGoalModal = false" class="btn-cancel">Cancelar</button>
            <button type="submit" class="btn-primary">Crear Meta</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Habit Modal -->
    <div v-if="showHabitModal" class="modal-overlay" @click="showHabitModal = false">
      <div class="modal-content" @click.stop>
        <h3>Nuevo Hábito</h3>
        <form @submit.prevent="createHabit">
          <div class="form-group">
            <label>Título:</label>
            <input v-model="newHabit.title" required class="form-input" />
          </div>
          <div class="form-group">
            <label>Descripción:</label>
            <textarea v-model="newHabit.description" class="form-textarea"></textarea>
          </div>
          <div class="form-group">
            <label>Frecuencia:</label>
            <select v-model="newHabit.frequency" class="form-select">
              <option value="daily">Diario</option>
              <option value="weekly">Semanal</option>
              <option value="monthly">Mensual</option>
            </select>
          </div>
          <div class="form-group">
            <label>Hora objetivo:</label>
            <input type="time" v-model="newHabit.target_time" class="form-input" />
          </div>
          <div class="form-group">
            <label>Dificultad:</label>
            <select v-model="newHabit.difficulty" class="form-select">
              <option value="easy">Fácil</option>
              <option value="medium">Media</option>
              <option value="hard">Difícil</option>
            </select>
          </div>
          <div class="form-actions">
            <button type="button" @click="showHabitModal = false" class="btn-cancel">Cancelar</button>
            <button type="submit" class="btn-primary">Crear Hábito</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

// Data
const selectedDate = ref(new Date().toISOString().split('T')[0])
const taskFilter = ref('all')
const currentMood = ref('neutral')
const energyLevel = ref(5)
const stressLevel = ref(5)
const dailyNotes = ref('')

// Modals
const showTaskModal = ref(false)
const showGoalModal = ref(false)
const showHabitModal = ref(false)

// New item data
const newTask = ref({
  title: '',
  description: '',
  category: 'work',
  priority: 'medium',
  due_date: '',
  estimated_minutes: 30,
})

const newGoal = ref({
  title: '',
  description: '',
  category: 'career',
  target_date: '',
  milestonesText: '',
  daily_focus: false,
  vision_board: false,
})

const newHabit = ref({
  title: '',
  description: '',
  frequency: 'daily',
  target_time: '',
  difficulty: 'medium',
})

// Data from API
const summary = ref({
  tasks_completed: 0,
  tasks_total: 0,
  habits_completed: 0,
  habits_total: 0,
  habits_completion_rate: 0,
  goals_total_progress: 0,
  goals_total: 0,
  pc_usage: {
    total_minutes: 0,
    productive_minutes: 0,
    entertainment_minutes: 0,
  },
})

const tasks = ref([])
const goals = ref([])
const habits = ref([])
const advices = ref([])
const pcUsage = ref({
  total_minutes: 0,
  productive_minutes: 0,
  entertainment_minutes: 0,
})

const activeSession = ref<Record<string, any> | null>(null)
const sessionStartTime = ref<Date | null>(null)
const sessionProductivity = ref(5)

// Computed
const filteredTasks = computed(() => {
  if (taskFilter.value === 'all') return tasks.value
  return tasks.value.filter(task => task.category === taskFilter.value)
})

// Methods
const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })
}

const loadDayData = async () => {
  try {
    const response = await axios.get(`/api/life-management/summary?date=${selectedDate.value}`)
    summary.value = response.data.summary
  } catch (error) {
    console.error('Error loading day data:', error)
  }
}

const loadTasks = async () => {
  try {
    const response = await axios.get('/api/life-management/tasks')
    tasks.value = response.data.tasks
  } catch (error) {
    console.error('Error loading tasks:', error)
  }
}

const loadGoals = async () => {
  try {
    const response = await axios.get('/api/life-management/goals')
    goals.value = response.data.goals
  } catch (error) {
    console.error('Error loading goals:', error)
  }
}

const loadHabits = async () => {
  try {
    const response = await axios.get('/api/life-management/habits')
    habits.value = response.data.habits
  } catch (error) {
    console.error('Error loading habits:', error)
  }
}

const loadAdvice = async () => {
  try {
    const response = await axios.get('/api/life-management/advice/today')
    advices.value = response.data.advice
  } catch (error) {
    console.error('Error loading advice:', error)
  }
}

const loadPCUsage = async () => {
  try {
    const response = await axios.get(`/api/life-management/pc/usage/${selectedDate.value}`)
    pcUsage.value = response.data.usage
  } catch (error) {
    console.error('Error loading PC usage:', error)
  }
}

const createTask = async () => {
  try {
    const response = await axios.post('/api/life-management/tasks', newTask.value)
    tasks.value.push(response.data.task)
    showTaskModal.value = false
    // Reset form
    newTask.value = {
      title: '',
      description: '',
      category: 'work',
      priority: 'medium',
      due_date: '',
      estimated_minutes: 30,
    }
  } catch (error) {
    console.error('Error creating task:', error)
  }
}

const completeTask = async (taskId: string) => {
  try {
    await axios.put(`/api/life-management/tasks/${taskId}/status`, { status: 'completed' })
    const task = tasks.value.find(t => t.task_id === taskId)
    if (task) task.status = 'completed'
  } catch (error) {
    console.error('Error completing task:', error)
  }
}

const deleteTask = async (taskId: string) => {
  try {
    await axios.delete(`/api/life-management/tasks/${taskId}`)
    tasks.value = tasks.value.filter(t => t.task_id !== taskId)
  } catch (error) {
    console.error('Error deleting task:', error)
  }
}

const createGoal = async () => {
  try {
    const response = await axios.post('/api/life-management/goals', {
      ...newGoal.value,
      milestones: newGoal.value.milestonesText.split(',').map(m => m.trim()),
    })
    goals.value.push(response.data.goal)
    showGoalModal.value = false
    // Reset form
    newGoal.value = {
      title: '',
      description: '',
      category: 'career',
      target_date: '',
      milestonesText: '',
      daily_focus: false,
      vision_board: false,
    }
  } catch (error) {
    console.error('Error creating goal:', error)
  }
}

const updateGoalProgress = async (goalId: string) => {
  const progress = prompt('Nuevo progreso (0-100):')
  if (progress) {
    try {
      await axios.put(`/api/life-management/goals/${goalId}/progress`, { progress: parseInt(progress) })
      const goal = goals.value.find(g => g.goal_id === goalId)
      if (goal) goal.progress_percentage = parseInt(progress)
    } catch (error) {
      console.error('Error updating goal progress:', error)
    }
  }
}

const deleteGoal = async (goalId: string) => {
  try {
    await axios.delete(`/api/life-management/goals/${goalId}`)
    goals.value = goals.value.filter(g => g.goal_id !== goalId)
  } catch (error) {
    console.error('Error deleting goal:', error)
  }
}

const createHabit = async () => {
  try {
    const response = await axios.post('/api/life-management/habits', newHabit.value)
    habits.value.push(response.data.habit)
    showHabitModal.value = false
    // Reset form
    newHabit.value = {
      title: '',
      description: '',
      frequency: 'daily',
      target_time: '',
      difficulty: 'medium',
    }
  } catch (error) {
    console.error('Error creating habit:', error)
  }
}

const logHabitEntry = async (habitId: string) => {
  try {
    await axios.post(`/api/life-management/habits/${habitId}/entry`, {
      completed: true,
      mood_before: currentMood.value,
      mood_after: currentMood.value,
    })
    const habit = habits.value.find(h => h.habit_id === habitId)
    if (habit) habit.streak_days += 1
  } catch (error) {
    console.error('Error logging habit entry:', error)
  }
}

const deleteHabit = async (habitId: string) => {
  try {
    await axios.delete(`/api/life-management/habits/${habitId}`)
    habits.value = habits.value.filter(h => h.habit_id !== habitId)
  } catch (error) {
    console.error('Error deleting habit:', error)
  }
}

const saveDailyMood = async () => {
  try {
    await axios.post('/api/life-management/mood', {
      mood_morning: currentMood.value,
      energy_level: energyLevel.value,
      stress_level: stressLevel.value,
      notes: dailyNotes.value,
    })
    alert('Estado de ánimo guardado')
  } catch (error) {
    console.error('Error saving daily mood:', error)
  }
}

const generateAdvice = async () => {
  try {
    const response = await axios.post('/api/life-management/advice', {
      category: 'productivity',
      context: { mood: currentMood.value, energy: energyLevel.value },
    })
    advices.value.unshift(response.data.advice)
  } catch (error) {
    console.error('Error generating advice:', error)
  }
}

const markAdviceHelpful = async (adviceId: string) => {
  // Implementar marcado como helpful
  advices.value = advices.value.filter(a => a.advice_id !== adviceId)
}

const dismissAdvice = (adviceId: string) => {
  advices.value = advices.value.filter(a => a.advice_id !== adviceId)
}

const startPCSession = async () => {
  try {
    const response = await axios.post('/api/life-management/pc/session/start', {
      category: 'work',
    })
    activeSession.value = response.data.session
    sessionStartTime.value = new Date()
  } catch (error) {
    console.error('Error starting PC session:', error)
  }
}

const endPCSession = async () => {
  if (!activeSession.value) return

  try {
    await axios.post(`/api/life-management/pc/session/${activeSession.value.session_id}/end`, {
      productivity_score: sessionProductivity.value,
      task_completed: true,
    })
    activeSession.value = null
    sessionStartTime.value = null
    loadPCUsage()
  } catch (error) {
    console.error('Error ending PC session:', error)
  }
}

const getSessionDuration = () => {
  if (!sessionStartTime.value) return 0
  return Math.round((new Date().getTime() - sessionStartTime.value.getTime()) / 60000)
}

// Lifecycle
onMounted(() => {
  loadDayData()
  loadTasks()
  loadGoals()
  loadHabits()
  loadAdvice()
  loadPCUsage()
})
</script>

<style scoped>
.life-management-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  font-family: 'Inter', sans-serif;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
  color: #00f0ff;
}

.subtitle {
  color: #666;
  margin-bottom: 20px;
}

.date-selector input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 1rem;
}

.daily-summary-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 0%);
  border: 1px solid #00f0ff;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 30px;
  box-shadow: 0 4px 20px rgba(0, 240, 255, 0.3);
}

.daily-summary-card h2 {
  color: #00f0ff;
  margin-bottom: 20px;
  font-size: 1.5rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.summary-item {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 12px;
  padding: 15px;
}

.summary-label {
  color: #00f0ff;
  font-size: 0.9rem;
  margin-bottom: 5px;
}

.summary-value {
  color: #fff;
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 10px;
}

.summary-bar {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  height: 8px;
  overflow: hidden;
}

.summary-progress {
  background: linear-gradient(90deg, #00f0ff, #00ff88);
  height: 100%;
  border-radius: 10px;
  transition: width 0.3s ease;
}

.main-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 20px;
}

.section-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 0%);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0, 240, 255, 0.2);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  color: #00f0ff;
  font-size: 1.3rem;
  margin: 0;
}

.filter-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.filter-tabs button {
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  color: #fff;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.filter-tabs button:hover {
  background: rgba(0, 240, oud 0.2);
}

.filter-tabs button.active {
  background: #00f0ff;
  color: #000;
}

.tasks-list,
.goals-list,
.habits-list,
.advice-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.task-item,
.goal-item,
.habit-item,
.advice-item {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 12px;
  padding: 15px;
  display: flex;
  align-items: center;
  gap: 15px;
}

.task-priority {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.task-priority.critical { background: #ff6b35; }
.task-priority.high { background: #ffaa00; }
.task-priority.medium { background: #00ff88; }
.task-priority.low { background: #00f0ff; }

.task-content,
.goal-content,
.habit-content,
.advice-content {
  flex: 1;
}

.task-title,
.goal-title,
.habit-title,
.advice-title {
  color: #fff;
  font-weight: 600;
  margin-bottom: 5px;
}

.task-meta,
.goal-meta,
.habit-meta {
  color: #888;
  font-size: 0.85rem;
  display: flex;
  gap: 10px;
}

.goal-progress-bar {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  height: 6px;
  overflow: hidden;
  margin-top: 10px;
}

.goal-progress-fill {
  background: linear-gradient(90deg, #00f0ff, #00ff88);
  height: 100%;
  border-radius: 10px;
  transition: width 0.3s ease;
}

.task-actions,
.goal-actions,
.habit-actions,
.advice-actions {
  display: flex;
  gap: 8px;
}

.btn-complete,
.btn-log,
.btn-helpful {
  background: #00ff88;
  color: #000;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-complete:hover,
.btn-log:hover,
.btn-helpful:hover {
  background: #00ffaa;
}

.btn-delete,
.btn-dismiss {
  background: #ff6b35;
  color: #fff;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-delete:hover,
.btn-dismiss:hover {
  background: #ff8555;
}

.btn-progress {
  background: #00f0ff;
  color: #000;
  border: none;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-progress:hover {
  background: #66f0ff;
}

.mood-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.mood-input,
.energy-input,
.stress-input,
.notes-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mood-input label,
.energy-input label,
.stress-input label,
.notes-input label {
  color: #00f0ff;
  font-size: 0.9rem;
}

.mood-selector {
  display: flex;
  gap: 10px;
}

.mood-selector button {
  font-size: 1.5rem;
  background: rgba(0, 240, 255, 0.1);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 8px;
  padding: 10px 15px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.mood-selector button:hover {
  background: rgba(0, 240, 255, 0.2);
}

.mood-selector button.active {
  background: #00f0ff;
  border-color: #00f0ff;
  transform: scale(1.1);
}

.energy-slider,
.stress-slider {
  width: 100%;
  height: 8px;
  border-radius: 5px;
  cursor: pointer;
}

.energy-value,
.stress-value {
  color: #00f0ff;
  font-weight: bold;
  margin-left: 10px;
}

.notes-textarea {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 8px;
  color: #fff;
  padding: 12px;
  min-height: 100px;
  resize: vertical;
  font-family: 'Inter', sans-serif;
}

.btn-save {
  background: #00f0ff;
  color: #000;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-save:hover {
  background: #66f0ff;
}

.btn-primary {
  background: #00f0ff;
  color: #000;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-primary:hover {
  background: #66f0ff;
}

.btn-secondary {
  background: rgba(0, 240, 255, 0.1);
  color: #00f0ff;
  border: 1px solid #00f0ff;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.0.3s ease;
}

.btn-secondary:hover {
  background: rgba(0, 240, 255, 0.2);
}

.btn-danger {
  background: #ff6b35;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-danger:hover {
  background: #ff8555;
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.btn-cancel:hover {
  background: rgba(255, 255, 255, 0.2);
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
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 0%);
  border: 1px solid #00f0ff;
  border-radius: 16px;
  padding: 30px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-content h3 {
  color: #00f0ff;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  color: #00f0ff;
  margin-bottom: 5px;
  font-size: 0.9rem;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.3);
  border-radius: 8px;
  color: #fff;
  padding: 10px;
  font-family: 'Inter', sans-serif;
  font-size: 0.95rem;
}

.form-textarea {
  min-height: 80px;
  resize: vertical;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  cursor: pointer;
}

.form-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.active-session-info {
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid #00ff88;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 15px;
}

.session-info {
  display: flex;
  gap: 15px;
  color: #00ff88;
  font-size: 0.9rem;
}

.pc-usage-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
}

.stat-item {
  background: rgba(0, 240, 255, 0.05);
  border: 1px solid rgba(0, 240, 255, 0.2);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.stat-label {
  color: #00f0ff;
  font-size: 0.85rem;
  margin-bottom: 5px;
}

.stat-value {
  color: #fff;
  font-size: 1.2rem;
  font-weight: bold;
}

.task-item.completed {
  opacity: 0.5;
  text-decoration: line-through;
}

.goal-item.on-track {
  border-color: #00ff88;
}

.goal-item.behind {
  border-color: #ffaa00;
}

.goal-item.completed {
  border-color: #00f0ff;
  opacity: 0.5;
}

.habit-item.paused {
  opacity: 0.5;
}

.advice-category {
  color: #00f0ff;
  font-size: 0.8rem;
  text-transform: uppercase;
  margin-bottom: 5px;
}

.advice-content {
  color: #ccc;
  font-size: 0.9rem;
  margin-bottom: 10px;
  line-height: 1.5;
}
</style>
