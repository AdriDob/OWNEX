# Rastro Fixes Summary

## Immediate Critical Fixes

### 1. Scheduler Copilot Integration Fix
**File:** `api/scheduler.py`
- Added null check before calling `copilot.recommend_for_system()`
- Prevents AttributeError when copilot is not initialized
- Location: line 424-441

### 2. PlaywrightSensor Integration Strategy
**Status:** IN PROGRESS - Architecture needs refactoring

**Problem:** PlaywrightSensor currently bypasses core Sensor architecture and fails to register properly with events.

**Solution:** 
- Refactor to properly inherit from `Sensor` base class
- Integrate into Universal Sensor Network via `observation_engine.py`
- Register in CapabilityRegistry for discovery

**Files to Modify:**
- `extensions/playwright/playwright_sensor.py` - refactor to proper Sensor
- `core/sensors/observation_engine.py` - add PlaywrightSensor registration
- `core/capabilities/registry.py` - ensure capability registration

## Capability Registry Integration

### Current Issues:
1. **Centralized Capability Registry** (`core/capabilities/registry.py`) exists but is unused by major components
2. **PlaywrightSensor** creates capability registration attempt but it's incomplete
3. **Core modules** like `coder_agent.py`, `execution/`, `commands/` bypass the registry

### Integration Strategy:
1. **Fix PlaywrightSensor** to properly register capability
2. **Update Core Modules** to use CapabilityRegistry for tool discovery
3. **Create CapabilityAdapter** for seamless integration

## Implementation Plan

### Phase 1: Fix PlaywrightSensor (High Priority)
```bash
# 1. Refactor PlaywrightSensor to proper Sensor base class
# 2. Register with Universal Sensor Network
# 3. Fix capability registration
# 4. Add heartbeat and health monitoring
```

### Phase 2: Capability Registry Integration
```bash
# 1. Adapt core/autonomy/coder_agent.py to use CapabilityRegistry
# 2. Update execution/ modules for registry-based tool selection
# 3. Fix commands/ dispatcher to register capabilities
# 4. Create CapabilityAdapter for smooth integration
```

### Phase 3: Installation Script
```bash
# Create simple installation script that:
# 1. Sets up virtual environment
# 2. Installs dependencies from pyproject.toml
# 3. Configures .env with proper settings
# 4. Runs verification checks
```

## Verification Checklist

- [ ] Scheduler null checks
- [ ] PlaywrightSensor proper inheritance
- [ ] CapabilityRegistry integration
- [ ] Installation script working
- [ ] Basic functionality test
- [ ] Configuration validation

## Next Steps

1. **Implement Phase 1 fixes** (immediate priority)
2. **Create installation script** for daily user use
3. **Run integration tests** to verify fixes
4. **Update documentation** with clear instructions

The system should be ready for daily user installation after these fixes are implemented.