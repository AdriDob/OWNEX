"""MT5 Bridge client for OWNEX trading integration.

Provides status, arm, disarm, kill and position queries via HTTP bridge.
Never exposes MT5 credentials to the frontend.
"""

from . import bridge_client, session, risk

__all__ = ["get_status", "arm_session", "disarm_session", "kill_session", "get_positions", "can_trade"]
