#!/usr/bin/env python3
"""
Rastro Validation Script (Targeted, lightweight)
Validates EventBus unification, Scheduler, Sensor network integration, imports.
"""
import sys
import traceback

def run_check(name, check_fn):
    try:
        check_fn()
        print(f'✓ {name}')
        return True
    except Exception as e:
        print(f'❌ {name}: {e}')
        traceback.print_exc()
        return False

def check_imports():
    # New EventBus
    from cores.events.event_bus import get_event_bus, EventBus as NewEventBus
    bus = get_event_bus()
    assert isinstance(bus, NewEventBus), f'bus is {type(bus)}, expected NewEventBus'

    # Legacy core EventBus (should still be accessible)
    from core.events.event_bus import get_core_event_bus, CoreEventBus as LegacyEventBus
    core_bus = get_core_event_bus()
    assert isinstance(core_bus, LegacyEventBus), f'core_bus is {type(core_bus)}, expected Legacy'

    # Scheduler instance and its copilot guard
    from api.scheduler import scheduler_instance, _get_copilot
    assert scheduler_instance is not None, 'scheduler_instance is None'
    assert _get_copilot() is None, 'Expected copilot to be None (deps not available)'

    # Sensor network imports
    from core.sensors.observation_engine import ObservationEngine
    from extensions.playwright.playwright_sensor import PlaywrightSensor
    print('  Imported all sensor components')

    # Check that ObservationEngine's reference to bus matches new EventBus
    obs = ObservationEngine(event_bus=bus)
    assert obs._bus is bus

    print('  All imports and basic instantiations OK')

def check_eventbus_enabled():
    from cores.events.event_bus import get_event_bus
    bus = get_event_bus()
    # New EventBus should have subscribe and publish methods
    assert hasattr(bus, 'subscribe'), 'New bus lacks subscribe'
    assert hasattr(bus, 'publish'), 'New bus lacks publish'
    # Ensure legacy bridge is disabled
    if hasattr(bus, 'disable_bridge'):
        bus.disable_bridge()
    # Here we just verify that everything is wired

def check_scheduler_copilot_guard():
    from api.scheduler import scheduler_instance
    import inspect
    source = inspect.getsource(scheduler_instance._copilot_hook)
    assert 'return' in source and '_get_copilot' in source, 'Missing guard against None copilot'

# Main
def main():
    print('=' * 60)
    print('Rastro Release Candidate - Targeted Validation')
    print('=' * 60)

    checks = [
        ('EventBus & Scheduler imports', check_imports),
        ('EventBus core functionality', check_eventbus_enabled),
        ('Scheduler copilot guard', check_scheduler_copilot_guard),
    ]

    passed = 0
    for name, fn in checks:
        if run_check(name, fn):
            passed += 1

    print()
    print('Summary:', passed, '/', len(checks), 'checks passed')
    if passed == len(checks):
        print('✓ All validation checks passed')
        return 0
    else:
        print('❌ Some validation checks failed')
        return 1

if __name__ == '__main__':
    sys.exit(main())
