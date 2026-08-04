from typing import Any


class Clusterer:
    def cluster_endpoints(self, endpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for endpoint in endpoints:
            key = "/".join(endpoint.get("path", "").split("/")[1:3])
            grouped.setdefault(key, []).append(endpoint)
        return [{"group": group, "count": len(items), "members": items} for group, items in grouped.items()]
