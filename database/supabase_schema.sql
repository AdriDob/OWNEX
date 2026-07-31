-- Supabase SQL Schema — OWNEX OMEGA Life Management + Auth

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla de tasks (gestión de tareas)
CREATE TABLE IF NOT EXISTS tasks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    task_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending', -- pending, in_progress, completed, cancelled
    priority TEXT DEFAULT 'medium', -- critical, high, medium, low
    category TEXT DEFAULT 'work', -- work, personal, health, finance, learning, social, home, hobby
    due_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    tags TEXT[],
    subtasks JSONB,
    linked_goal_id TEXT,
    linked_habit_id TEXT,
    estimated_time INTEGER, -- minutes
    actual_time INTEGER -- minutes
);

-- Tabla de goals (metas a largo plazo)
CREATE TABLE IF NOT EXISTS goals (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    goal_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'in_progress', -- not_started, in_progress, completed, on_hold
    category TEXT DEFAULT 'personal', -- career, health, finance, learning, personal_growth, relationships, travel, other
    target_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    progress INTEGER DEFAULT 0, -- 0-100
    vision_board TEXT, -- URL to image
    daily_focus TEXT,
    journaling TEXT
);

-- Tabla de habits (hábitos diarios)
CREATE TABLE IF NOT EXISTS habits (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    habit_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active', -- active, paused, completed
    frequency TEXT DEFAULT 'daily', -- daily, weekly, monthly
    created_at TIMESTAMP DEFAULT NOW(),
    last_completed_at TIMESTAMP,
    streak INTEGER DEFAULT 0,
    difficulty TEXT DEFAULT 'medium', -- easy, medium, hard
    reward TEXT,
    linked_goal_id TEXT
);

-- Tabla de habit_entries (entradas de hábitos)
CREATE TABLE IF NOT EXISTS habit_entries (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    habit_id TEXT REFERENCES habits(habit_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    mood_before TEXT, -- positive, neutral, negative
    mood_after TEXT,
    energy_level INTEGER, -- 1-10
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(habit_id, date)
);

-- Tabla de daily_moods (estado de ánimo diario)
CREATE TABLE IF NOT EXISTS daily_moods (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE UNIQUE NOT NULL,
    mood TEXT NOT NULL, -- very_positive, positive, neutral, negative, very_negative
    energy_level INTEGER, -- 1-10
    stress_level INTEGER, -- 1-10
    sleep_quality INTEGER, -- 1-10
    gratitude_journal TEXT,
    challenges TEXT,
    achievements TEXT,
    daily_notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabla de pc_usage_sessions (sesiones de uso de PC)
CREATE TABLE IF NOT EXISTS pc_usage_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration INTEGER, -- minutes
    productivity_score INTEGER, -- 1-10
    distractions TEXT[],
    productive_time INTEGER, -- minutes
    entertainment_time INTEGER, -- minutes
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_goals_user_id ON goals(user_id);
CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status);
CREATE INDEX IF NOT EXISTS idx_habits_user_id ON habits(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_entries_user_id ON habit_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_habit_entries_date ON habit_entries(date);
CREATE INDEX IF NOT EXISTS idx_daily_moods_user_id ON daily_moods(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_moods_date ON daily_moods(date);
CREATE INDEX IF NOT EXISTS idx_pc_usage_sessions_user_id ON pc_usage_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_pc_usage_sessions_start_time ON pc_usage_sessions(start_time);

-- Row Level Security (RLS) policies
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE habits ENABLE ROW LEVEL SECURITY;
ALTER TABLE habit_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_moods ENABLE ROW LEVEL SECURITY;
ALTER TABLE pc_usage_sessions ENABLE ROW LEVEL SECURITY;

-- Policies: Users solo pueden ver/editar sus propios datos
CREATE POLICY "Users can view own tasks" ON tasks FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own tasks" ON tasks FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own tasks" ON tasks FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own tasks" ON tasks FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own goals" ON goals FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own goals" ON goals FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own goals" ON goals FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own goals" ON goals FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own habits" ON habits FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own habits" ON habits FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own habits" ON habits FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own habits" ON habits FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own habit_entries" ON habit_entries FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own habit_entries" ON habit_entries FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own habit_entries" ON habit_entries FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own habit_entries" ON habit_entries FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own daily_moods" ON daily_moods FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own daily_moods" ON daily_moods FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own daily_moods" ON daily_moods FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own daily_moods" ON daily_moods FOR DELETE USING (auth.uid() = user_id);

CREATE POLICY "Users can view own pc_usage_sessions" ON pc_usage_sessions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own pc_usage_sessions" ON pc_usage_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own pc_usage_sessions" ON pc_usage_sessions FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own pc_usage_sessions" ON pc_usage_sessions FOR DELETE USING (auth.uid() = user_id);
