# OWNEX OMEGA — Quick Start Guide

## What is OWNEX?

OWNEX OMEGA is an **Autonomous Personal Operating System** that helps you learn, create, work, and evolve with artificial intelligence.

## What can OWNEX do?

OWNEX autonomously:

- **Bug Bounty** - Automatically discover and report security vulnerabilities
- **Software Development** - Generate, review, and improve code
- **Revenue Generation** - Find and exploit opportunities across platforms
- **Knowledge Management** - Learn from every action and improve over time
- **Task Automation** - Run workflows 24/7 without intervention
- **Voice Control** - Control the system with natural language commands
- **Mobile Access** - Monitor and control from your phone and smartwatch

## Quick Start (5 minutes)

### 1. Install Requirements

```bash
# Clone the repository
git clone https://github.com/AdriDob/rastrohunteralpha.git
cd rastrohunteralpha

# Install Python dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
# Add your AI provider keys (OpenRouter, Ollama, etc.)
```

### 3. Start OWNEX ALPHA (Desktop)

```bash
# Start the backend
python api/main.py

# Start the frontend (in another terminal)
cd frontend
npm install
npm run dev
```

OWNEX ALPHA will open at http://localhost:5173

### 4. Start AI Providers

OWNEX supports multiple AI providers. Configure at least one:

**Option 1: Ollama (Local - Free)**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull qwen3-coder:8b
```

**Option 2: OpenRouter (Free)**
```bash
# Add to .env
ANTHROPIC_API_KEY=your_openrouter_key
ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
```

**Option 3: OpenCode (Free)**
No configuration needed - built-in free models.

### 5. First Steps

1. **Mission Control** - Your central dashboard
   - Monitor agent activity
   - View system health
   - Check opportunities
   - Review findings

2. **MERLIN Assistant** - Your AI companion
   - Ask questions about the system
   - Get explanations for actions
   - Request recommendations
   - Learn from feedback

3. **Configure Work Cycles** - Automation schedules
   - Security Cycle (bug bounty)
   - Forge Cycle (dev bounty)
   - Pulse Cycle (AI work)
   - Vault Cycle (wealth management)

## Mobile Companion (OWNEX OMEGA)

### Requirements

- Android 10+
- Supabase account (free)

### Setup

1. **Configure Supabase**
   - Create free project at https://supabase.com
   - Copy Project URL and Anon Key
   - Add to `frontend/.env`:
     ```
     VITE_SUPABASE_URL=your_supabase_project_url
     VITE_SUPABASE_KEY=your_supabase_anon_key
     ```

2. **Build Android App**
   ```bash
   cd android
   ./gradlew assembleDebug
   ```

3. **Install APK**
   - APK will be in `android/app/build/outputs/apk/debug/app-debug.apk`
   - Install on your Android device

4. **Sync with Desktop**
   - Open OWNEX OMEGA on your phone
   - Enter your Supabase credentials
   - Desktop ALPHA will sync automatically

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (needs 3.11+)
- Check if .venv is activated
- Check if dependencies are installed: `pip list`

### Frontend won't start
- Check if npm is installed: `npm --version`
- Check if node_modules exists: `cd frontend && npm install`
- Check if port 5173 is available

### AI not working
- Check if Ollama is running: `ollama list`
- Check if API keys are configured in .env
- Check if network connection is available

### Mobile won't sync
- Check if Supabase is configured
- Check if backend is running
- Check if network connection is available

## Next Steps

1. Explore Mission Control dashboard
2. Talk to MERLIN to understand the system
3. Configure your first Work Cycle
4. Enable Voice Commands (if microphone available)
5. Set up mobile sync for on-the-go access

## Support

- **Documentation:** See `.ai/` directory for detailed technical docs
- **Issues:** Report bugs at https://github.com/AdriDob/rastrohunteralpha/issues
- **Community:** Join discussions in GitHub Issues

---

OWNEX OMEGA — Your autonomous operating system.
Build. Learn. Automate. Evolve.
