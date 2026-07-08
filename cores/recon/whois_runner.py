import asyncio
import logging
from pathlib import Path

import whois as whois_lib

logger = logging.getLogger("cateye.recon.whois")


class WhoisRunner:
    def __init__(self, output_dir: Path, timeout: int = 30):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    async def run_whois(self, domain: str, out_file: str = "whois.txt") -> Path:
        path = self.output_dir / out_file
        try:
            w = await asyncio.to_thread(whois_lib.whois, domain)
            lines = []
            for key in ("domain_name", "registrar", "creation_date", "expiration_date",
                         "updated_date", "name_servers", "status", "emails",
                         "org", "country", "city", "address"):
                val = w.get(key)
                if val:
                    if isinstance(val, list):
                        val = ", ".join(str(v) for v in val[:3])
                    lines.append(f"{key}: {val}")
            path.write_text("\n".join(lines) if lines else "No WHOIS data returned")
        except Exception as e:
            path.write_text(f"WHOIS ERROR: {e}")
        return path
