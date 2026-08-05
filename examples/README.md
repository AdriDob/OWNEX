# OWNEX Usage Examples

This directory contains practical usage examples for OWNEX.

## Examples

### 1. Basic Quick Start
```bash
# Clone and setup
git clone https://github.com/AdriDob/rastrohunteralpha.git
cd rastrohunteralpha

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start services
make dev
```

### 2. Security Research Cycle
```python
# Example: Run a security research cycle
from core.cycles.security import SecurityCycle

cycle = SecurityCycle()
results = await cycle.execute(
    target="example.com",
    scope=["web", "api"],
    depth="comprehensive"
)
print(f"Found {len(results.findings)} vulnerabilities")
```

### 3. Opportunity Discovery
```python
# Example: Discover revenue opportunities
from core.opportunity import get_opportunity_engine

engine = get_opportunity_engine()
opportunities = await engine.discover(
    categories=["bug_bounty", "freelance", "grants"],
    min_score=70
)
for opp in opportunities:
    print(f"{opp.title}: ${opp.estimated_value}")
```

### 4. MERLIN Assistant
```python
# Example: Interact with MERLIN
from core.ai.merlin import Merlin

merlin = Merlin()
response = await merlin.chat(
    "Analyze my current bug bounty targets and suggest priorities"
)
print(response)
```

### 5. Custom Agent
```python
# Example: Create a custom autonomous agent
from core.agents.base import BaseAgent
from core.events import EventBus

class MyCustomAgent(BaseAgent):
    async def execute(self, task):
        # Your custom logic here
        result = await self.process_task(task)
        await self.emit(Event("task_completed", result))
        return result
```

### 6. Mobile Companion
```bash
# Android build
cd android
./gradlew assembleDebug

# Wear OS build
cd wearos
./gradlew assembleDebug
```

---

See the [main README](../README.md) for complete documentation.