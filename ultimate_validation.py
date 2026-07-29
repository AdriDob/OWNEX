#!/usr/bin/env python3
"""
Rastro Validation Script - Complete EventBus unification check
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

def main():
    print('Starting Rastro EventBus unification validation...')
    
    # Import checks
    def check_new_eventbus():
        from cores.events.event_bus import get_event_bus, EventBus
        bus = get_event_bus()
        assert isinstance(bus, EventBus), f'Expected EventBus, got {type(bus)}'
        print('  New EventBus: OK')
    
    def check_legacy_eventbus():
        from core.events.event_bus import get_core_event_bus
        bus = get_core_event_bus()
        print(f'  Legacy EventBus: OK ({type(bus).__name__})')
    
    def check_eventstore():
        from cores.events.store import get_event_store
        store = get_event_store()
        print(f'  EventStore: OK ({type(store).__name__})')
    
    def check_event_store_new_namespace():
        from cores.events.store import get_event_store
        assert get_event_store() is not None
        print('  EventStore (cores.* namespace): OK')
    
    def check_event_store_legacy_namespace():
        from core.events.store import get_event_store
        assert get_event_store() is not None
        print('  EventStore (core.* namespace): OK')
    
    checks = [
        ('New EventBus import', check_new_eventbus),
        ('Legacy EventBus import', check_legacy_eventbus),
        ('EventStore import', check_eventstore),
        ('EventStore (cores.* namespace)', check_event_store_new_namespace),
        ('EventStore (core.* namespace)', check_event_store_legacy_namespace),
        ('Scheduler module import', lambda: __import__('api.scheduler')),
        ('Main API module', lambda: __import__('api.main')),
        ('Capability registry', lambda: __import__('core.capabilities.registry')),
    ]
    
    passed = 0
    for name, check in checks:
        if run_check(name, check):
            passed += 1
    
    print()
    print('Final validation summary:', passed, '/', len(checks), 'checks passed')
    if passed == len(checks):
        print('✓ All EventBus unification checks passed!')
        sys.exit(0)
    else:
        print('❌ Some checks failed')
        sys.exit(1)

if __name__ == '__main__':
    main()

