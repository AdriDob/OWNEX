from unittest.mock import MagicMock


def _make_response(status: int, json_data: dict) -> MagicMock:
    """Create a mock HTTP response (sync methods)."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp
