from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field

from core.revenue_multiplier.models import ToolCategory, ToolStatus

logger = logging.getLogger("orion.revenue.tool_registry")


@dataclass
class ToolDef:
    name: str
    category: ToolCategory
    description: str
    binary: str = ""
    pip_package: str = ""
    npm_package: str = ""
    github_url: str = ""
    keywords: list[str] = field(default_factory=list)
    min_ram_gb: float = 0.5
    requires_api_key: bool = False
    install_hint: str = ""
    adapter: str = ""


TOOLS: list[ToolDef] = [
    # ── Reconnaissance ──
    ToolDef(
        "subfinder",
        ToolCategory.RECON,
        "Passive subdomain discovery",
        binary="subfinder",
        github_url="https://github.com/projectdiscovery/subfinder",
        keywords=["subdomain", "passive"],
        install_hint="go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
    ),
    ToolDef(
        "assetfinder",
        ToolCategory.RECON,
        "Find subdomains from various sources",
        binary="assetfinder",
        github_url="https://github.com/tomnomnom/assetfinder",
        keywords=["subdomain", "passive"],
        install_hint="go install github.com/tomnomnom/assetfinder@latest",
    ),
    ToolDef(
        "amass",
        ToolCategory.RECON,
        "In-depth subdomain enumeration",
        binary="amass",
        github_url="https://github.com/owasp-amass/amass",
        keywords=["subdomain", "enumeration"],
        install_hint="go install -v github.com/owasp-amass/amass/v4/...@master",
    ),
    ToolDef(
        "findomain",
        ToolCategory.RECON,
        "Monitoring subdomain finder",
        binary="findomain",
        github_url="https://github.com/Findomain/Findomain",
        keywords=["subdomain", "monitoring"],
        install_hint="cargo install findomain",
    ),
    ToolDef(
        "shuffledns",
        ToolCategory.RECON,
        "Massive DNS resolver",
        binary="shuffledns",
        github_url="https://github.com/projectdiscovery/shuffledns",
        keywords=["dns", "resolve"],
        install_hint="go install -v github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest",
    ),
    ToolDef(
        "puredns",
        ToolCategory.RECON,
        "Wildcard-resistant DNS resolver",
        binary="puredns",
        github_url="https://github.com/d3mondev/puredns",
        keywords=["dns", "wildcard"],
        install_hint="go install github.com/d3mondev/puredns/v2@latest",
    ),
    ToolDef(
        "naabu",
        ToolCategory.RECON,
        "Fast port scanner",
        binary="naabu",
        github_url="https://github.com/projectdiscovery/naabu",
        keywords=["port", "scan"],
        install_hint="go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest",
    ),
    ToolDef(
        "httpx",
        ToolCategory.RECON,
        "HTTP probe and response analysis",
        binary="httpx",
        github_url="https://github.com/projectdiscovery/httpx",
        keywords=["http", "probe"],
        install_hint="go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest",
    ),
    ToolDef(
        "gau",
        ToolCategory.RECON,
        "Get all URLs from Wayback/etc",
        binary="gau",
        github_url="https://github.com/lc/gau",
        keywords=["urls", "wayback"],
        install_hint="go install github.com/lc/gau/v2/cmd/gau@latest",
    ),
    ToolDef(
        "waymore",
        ToolCategory.RECON,
        "More URLs from Wayback Machine",
        binary="waymore",
        github_url="https://github.com/xnl-h4ck3r/waymore",
        keywords=["urls", "wayback", "archives"],
        install_hint="pip install waymore",
    ),
    ToolDef(
        "katana",
        ToolCategory.RECON,
        "Crawler and URL discovery",
        binary="katana",
        github_url="https://github.com/projectdiscovery/katana",
        keywords=["crawl", "spider"],
        install_hint="go install -v github.com/projectdiscovery/katana/cmd/katana@latest",
    ),
    ToolDef(
        "hakrawler",
        ToolCategory.RECON,
        "Web crawler for endpoints",
        binary="hakrawler",
        github_url="https://github.com/hakluke/hakrawler",
        keywords=["crawl", "endpoints"],
        install_hint="go install github.com/hakluke/hakrawler@latest",
    ),
    ToolDef(
        "gospider",
        ToolCategory.RECON,
        "Fast web spider",
        binary="gospider",
        github_url="https://github.com/jaeles-project/gospider",
        keywords=["spider", "crawl"],
        install_hint="go install github.com/jaeles-project/gospider@latest",
    ),
    ToolDef(
        "uncover",
        ToolCategory.RECON,
        "Passive discovery from shodan/etc",
        binary="uncover",
        github_url="https://github.com/projectdiscovery/uncover",
        keywords=["passive", "shodan", "censys"],
        install_hint="go install -v github.com/projectdiscovery/uncover/cmd/uncover@latest",
    ),
    ToolDef(
        "tlsx",
        ToolCategory.RECON,
        "TLS/SSL certificate grabber",
        binary="tlsx",
        github_url="https://github.com/projectdiscovery/tlsx",
        keywords=["tls", "ssl", "certificate"],
        install_hint="go install -v github.com/projectdiscovery/tlsx/cmd/tlsx@latest",
    ),
    ToolDef(
        "chaos",
        ToolCategory.RECON,
        "Chaos DNS dataset client",
        binary="chaos",
        github_url="https://github.com/projectdiscovery/chaos-client",
        keywords=["dns", "dataset"],
        install_hint="go install -v github.com/projectdiscovery/chaos-client/cmd/chaos@latest",
        requires_api_key=True,
    ),
    # ── Scanning / Vulnerability Detection ──
    ToolDef(
        "nuclei",
        ToolCategory.SCANNER,
        "Fast vulnerability scanner with YAML templates",
        binary="nuclei",
        github_url="https://github.com/projectdiscovery/nuclei",
        keywords=["vuln", "template", "scan"],
        install_hint="go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        min_ram_gb=1.0,
    ),
    ToolDef(
        "jaeles",
        ToolCategory.SCANNER,
        "Flexible web scanner",
        binary="jaeles",
        github_url="https://github.com/jaeles-project/jaeles",
        keywords=["scan", "signature"],
        install_hint="go install github.com/jaeles-project/jaeles@latest",
    ),
    ToolDef(
        "nikto",
        ToolCategory.SCANNER,
        "Web server scanner",
        binary="nikto",
        keywords=["scan", "server"],
        install_hint="apt install nikto",
    ),
    ToolDef(
        "wpscan",
        ToolCategory.SCANNER,
        "WordPress vulnerability scanner",
        binary="wpscan",
        github_url="https://github.com/wpscanteam/wpscan",
        keywords=["wordpress", "cms"],
        install_hint="gem install wpscan",
        requires_api_key=True,
    ),
    # ── Fuzzing ──
    ToolDef(
        "ffuf",
        ToolCategory.FUZZING,
        "Fast web fuzzer",
        binary="ffuf",
        github_url="https://github.com/ffuf/ffuf",
        keywords=["fuzz", "directory"],
        install_hint="go install github.com/ffuf/ffuf/v2@latest",
    ),
    ToolDef(
        "feroxbuster",
        ToolCategory.FUZZING,
        "Recursive content discovery",
        binary="feroxbuster",
        github_url="https://github.com/epi052/feroxbuster",
        keywords=["fuzz", "discovery", "recursive"],
        install_hint="cargo install feroxbuster",
    ),
    ToolDef(
        "dirsearch",
        ToolCategory.FUZZING,
        "Dictionary-based web path scanner",
        pip_package="dirsearch",
        github_url="https://github.com/maurosoria/dirsearch",
        keywords=["directory", "bruteforce"],
        install_hint="pip install dirsearch",
    ),
    ToolDef(
        "gobuster",
        ToolCategory.FUZZING,
        "Directory/file/DNS busting",
        binary="gobuster",
        github_url="https://github.com/OJ/gobuster",
        keywords=["directory", "dns", "vhost"],
        install_hint="go install github.com/OJ/gobuster/v3@latest",
    ),
    ToolDef(
        "arjun",
        ToolCategory.FUZZING,
        "HTTP parameter discovery",
        pip_package="arjun",
        github_url="https://github.com/s0md3v/Arjun",
        keywords=["parameter", "discovery"],
        install_hint="pip install arjun",
    ),
    # ── Exploit / Injection ──
    ToolDef(
        "sqlmap",
        ToolCategory.EXPLOIT,
        "SQL injection automation",
        pip_package="sqlmap",
        github_url="https://github.com/sqlmapproject/sqlmap",
        keywords=["sqli", "database"],
        install_hint="pip install sqlmap",
    ),
    ToolDef(
        "nosqlmap",
        ToolCategory.EXPLOIT,
        "NoSQL injection scanner",
        pip_package="nosqlmap",
        github_url="https://github.com/codingo/NoSQLMap",
        keywords=["nosql", "mongodb"],
        install_hint="pip install nosqlmap",
    ),
    ToolDef(
        "xsstrike",
        ToolCategory.EXPLOIT,
        "XSS detection and exploitation",
        pip_package="xsstrike",
        github_url="https://github.com/s0md3v/XSStrike",
        keywords=["xss", "injection"],
        install_hint="pip install xsstrike",
    ),
    ToolDef(
        "dalfox",
        ToolCategory.EXPLOIT,
        "XSS scanning and parameter analysis",
        binary="dalfox",
        github_url="https://github.com/hahwul/dalfox",
        keywords=["xss", "scan"],
        install_hint="go install github.com/hahwul/dalfox/v2@latest",
    ),
    ToolDef(
        "crlfuzz",
        ToolCategory.EXPLOIT,
        "CRLF injection scanner",
        binary="crlfuzz",
        github_url="https://github.com/dwisiswant0/crlfuzz",
        keywords=["crlf", "injection"],
        install_hint="go install github.com/dwisiswant0/crlfuzz/cmd/crlfuzz@latest",
    ),
    ToolDef(
        "openredirex",
        ToolCategory.EXPLOIT,
        "Open redirect checker",
        binary="openredirex",
        github_url="https://github.com/devanshbatham/OpenRedireX",
        keywords=["redirect", "open-redirect"],
        install_hint="go install github.com/devanshbatham/openredirex@latest",
    ),
    ToolDef(
        "ssrfmap",
        ToolCategory.EXPLOIT,
        "SSRF exploitation tool",
        pip_package="ssrfmap",
        github_url="https://github.com/swisskyrepo/SSRFmap",
        keywords=["ssrf", "server-side"],
        install_hint="pip install ssrfmap",
    ),
    ToolDef(
        "gitleaks",
        ToolCategory.EXPLOIT,
        "Git secret scanner",
        binary="gitleaks",
        github_url="https://github.com/gitleaks/gitleaks",
        keywords=["secret", "git", "leak"],
        install_hint="go install github.com/gitleaks/gitleaks/v8@latest",
    ),
    ToolDef(
        "trufflehog",
        ToolCategory.EXPLOIT,
        "Credential scanner",
        binary="trufflehog",
        github_url="https://github.com/trufflesecurity/trufflehog",
        keywords=["secret", "credential"],
        install_hint="go install github.com/trufflesecurity/trufflehog/v3@latest",
    ),
    ToolDef(
        "qsreplace",
        ToolCategory.EXPLOIT,
        "Replace query string parameters",
        binary="qsreplace",
        github_url="https://github.com/tomnomnom/qsreplace",
        keywords=["parameter", "replace"],
        install_hint="go install github.com/tomnomnom/qsreplace@latest",
    ),
    ToolDef(
        "interactsh",
        ToolCategory.EXPLOIT,
        "Out-of-band interaction server",
        binary="interactsh-client",
        github_url="https://github.com/projectdiscovery/interactsh",
        keywords=["oob", "callback"],
        install_hint="go install -v github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest",
    ),
    # ── OSINT ──
    ToolDef(
        "shodan",
        ToolCategory.OSINT,
        "Shodan search engine integration",
        pip_package="shodan",
        keywords=["search", "iot", "services"],
        install_hint="pip install shodan",
        requires_api_key=True,
    ),
    ToolDef(
        "theHarvester",
        ToolCategory.OSINT,
        "Email/subdomain/name discovery",
        pip_package="theHarvester",
        github_url="https://github.com/laramies/theHarvester",
        keywords=["email", "domain", "discovery"],
        install_hint="pip install theHarvester",
    ),
    ToolDef(
        "holehe",
        ToolCategory.OSINT,
        "Email verification and OSINT",
        pip_package="holehe",
        github_url="https://github.com/megadose/holehe",
        keywords=["email", "verification"],
        install_hint="pip install holehe",
    ),
    # ── Crypto: Exchanges ──
    ToolDef(
        "ccxt",
        ToolCategory.CRYPTO_EXCHANGE,
        "Unified crypto exchange API",
        pip_package="ccxt",
        keywords=["exchange", "cex", "api"],
        install_hint="pip install ccxt",
    ),
    ToolDef(
        "freqtrade",
        ToolCategory.CRYPTO_EXCHANGE,
        "Crypto trading bot framework",
        pip_package="freqtrade",
        github_url="https://github.com/freqtrade/freqtrade",
        keywords=["trading", "bot", "strategy"],
        install_hint="pip install freqtrade",
        min_ram_gb=2.0,
    ),
    ToolDef(
        "hummingbot",
        ToolCategory.CRYPTO_EXCHANGE,
        "Market making bot",
        pip_package="hummingbot",
        github_url="https://github.com/hummingbot/hummingbot",
        keywords=["market-making", "liquidity"],
        install_hint="pip install hummingbot",
        min_ram_gb=2.0,
    ),
    # ── Crypto: DEX / Solana ──
    ToolDef(
        "solders",
        ToolCategory.CRYPTO_DEX,
        "Solana data structures",
        pip_package="solders",
        keywords=["solana", "sdk"],
        install_hint="pip install solders",
    ),
    ToolDef(
        "solana-py",
        ToolCategory.CRYPTO_DEX,
        "Solana Python SDK",
        pip_package="solana",
        keywords=["solana", "rpc"],
        install_hint="pip install solana",
    ),
    ToolDef(
        "jupiter",
        ToolCategory.CRYPTO_DEX,
        "Jupiter DEX aggregator API",
        keywords=["swap", "aggregator", "solana"],
        install_hint="No install needed — REST API",
    ),
    ToolDef(
        "birdeye",
        ToolCategory.CRYPTO_ANALYSIS,
        "Birdeye token data API",
        keywords=["tokens", "charts", "analysis"],
        install_hint="Get API key at birdeye.so",
        requires_api_key=True,
    ),
    ToolDef(
        "dexscreener",
        ToolCategory.CRYPTO_ANALYSIS,
        "DEX pair discovery and charts",
        keywords=["pairs", "liquidity", "chart"],
        install_hint="No install needed — REST API",
    ),
    ToolDef(
        "helius",
        ToolCategory.CRYPTO_ANALYSIS,
        "Solana enhanced RPC and webhooks",
        keywords=["solana", "rpc", "webhooks"],
        install_hint="Get API key at helius.dev",
        requires_api_key=True,
    ),
    # ── Browser Automation ──
    ToolDef(
        "playwright",
        ToolCategory.BROWSER,
        "Browser automation framework",
        pip_package="playwright",
        keywords=["browser", "automation", "screenshot"],
        install_hint="pip install playwright && playwright install chromium",
    ),
    ToolDef(
        "selenium",
        ToolCategory.BROWSER,
        "Legacy browser automation",
        pip_package="selenium",
        keywords=["browser", "automation"],
        install_hint="pip install selenium",
    ),
    # ── AI / LLM ──
    ToolDef(
        "langchain",
        ToolCategory.AI,
        "LLM orchestration framework",
        pip_package="langchain",
        keywords=["llm", "ai", "chain"],
        install_hint="pip install langchain",
    ),
    ToolDef(
        "llamaindex",
        ToolCategory.AI,
        "Data indexing for LLMs",
        pip_package="llama-index",
        keywords=["index", "rag", "llm"],
        install_hint="pip install llama-index",
    ),
    # ── Infrastructure ──
    ToolDef(
        "redis",
        ToolCategory.INFRASTRUCTURE,
        "In-memory cache and queue",
        pip_package="redis",
        keywords=["cache", "queue", "pubsub"],
        install_hint="apt install redis-server && pip install redis",
    ),
    ToolDef(
        "celery",
        ToolCategory.INFRASTRUCTURE,
        "Async task queue",
        pip_package="celery",
        keywords=["task", "queue", "async"],
        install_hint="pip install celery[redis]",
    ),
    # ── Revenue Multiplier: Polymarket ──
    ToolDef(
        "polymarket",
        ToolCategory.CRYPTO_DEX,
        "Polymarket prediction market trading",
        pip_package="",
        github_url="https://github.com/0xDesigner/polymarket-trading-bot-python-V2",
        keywords=["prediction", "markets", "polymarket", "clob"],
        install_hint="git clone https://github.com/0xDesigner/polymarket-trading-bot-python-V2",
        min_ram_gb=0.5,
    ),
    # ── Revenue Multiplier: Flumine (Betfair) ──
    ToolDef(
        "flumine",
        ToolCategory.AUTOMATION,
        "Betfair sports betting framework with event-driven architecture",
        pip_package="flumine",
        github_url="https://github.com/betcode-org/flumine",
        keywords=["betfair", "sports", "betting", "exchange"],
        install_hint="pip install flumine",
        min_ram_gb=1.0,
    ),
    # ── Revenue Multiplier: Jesse ──
    ToolDef(
        "jesse",
        ToolCategory.CRYPTO_EXCHANGE,
        "Crypto trading bot with zero look-ahead backtesting",
        pip_package="jesse",
        github_url="https://github.com/jesse-ai/jesse",
        keywords=["trading", "backtesting", "strategy"],
        install_hint="pip install jesse",
        min_ram_gb=2.0,
    ),
    # ── Revenue Multiplier: sports-betting (scikit-learn) ──
    ToolDef(
        "sports-betting",
        ToolCategory.AUTOMATION,
        "ML-powered sports betting with scikit-learn models",
        pip_package="sports-betting",
        github_url="https://github.com/georgedouzas/sports-betting",
        keywords=["sports", "betting", "ml", "scikit-learn"],
        install_hint="pip install sports-betting",
    ),
    ToolDef(
        "duckdb",
        ToolCategory.DATA,
        "In-process analytical SQL database",
        pip_package="duckdb",
        keywords=["database", "analytics", "sql"],
        install_hint="pip install duckdb",
    ),
    # ── Utilities ──
    ToolDef(
        "anew",
        ToolCategory.AUTOMATION,
        "Append and dedup lines",
        binary="anew",
        github_url="https://github.com/tomnomnom/anew",
        keywords=["dedup", "append"],
        install_hint="go install github.com/tomnomnom/anew@latest",
    ),
    ToolDef(
        "gf",
        ToolCategory.AUTOMATION,
        "Pattern matching with grep",
        binary="gf",
        github_url="https://github.com/tomnomnom/gf",
        keywords=["pattern", "grep"],
        install_hint="go install github.com/tomnomnom/gf@latest",
    ),
    ToolDef(
        "interlace",
        ToolCategory.AUTOMATION,
        "Parallel command executor",
        pip_package="interlace",
        github_url="https://github.com/codingo/Interlace",
        keywords=["parallel", "execution"],
        install_hint="pip install interlace",
    ),
]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}
        self._status_cache: dict[str, ToolStatus] = {}
        self._load()

    def _load(self) -> None:
        for t in TOOLS:
            self._tools[t.name] = t

    @property
    def count(self) -> int:
        return len(self._tools)

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def list_by_category(self, category: ToolCategory) -> list[ToolDef]:
        return [t for t in self._tools.values() if t.category == category]

    def list_by_keyword(self, keyword: str) -> list[ToolDef]:
        kw = keyword.lower()
        return [t for t in self._tools.values() if any(kw in k.lower() for k in t.keywords) or kw in t.name.lower()]

    def check_available(self, name: str) -> ToolStatus:
        if name in self._status_cache:
            return self._status_cache[name]

        tool = self._tools.get(name)
        if not tool:
            return ToolStatus.NOT_FOUND

        if tool.binary:
            status = ToolStatus.AVAILABLE if shutil.which(tool.binary) else ToolStatus.NOT_FOUND
        elif tool.pip_package:
            status = self._check_pip_package(tool.pip_package)
        else:
            status = ToolStatus.AVAILABLE

        self._status_cache[name] = status
        return status

    def check_all(self) -> dict[str, ToolStatus]:
        return {name: self.check_available(name) for name in self._tools}

    def get_available(self) -> list[ToolDef]:
        return [t for t in self._tools.values() if self.check_available(t.name) == ToolStatus.AVAILABLE]

    def get_unavailable(self) -> list[ToolDef]:
        return [t for t in self._tools.values() if self.check_available(t.name) == ToolStatus.NOT_FOUND]

    def get_summary(self) -> dict[str, int]:
        statuses = self.check_all()
        return {
            "total": len(statuses),
            "available": sum(1 for s in statuses.values() if s == ToolStatus.AVAILABLE),
            "not_found": sum(1 for s in statuses.values() if s == ToolStatus.NOT_FOUND),
            "error": sum(1 for s in statuses.values() if s == ToolStatus.ERROR),
        }

    def _check_pip_package(self, package: str) -> ToolStatus:
        try:
            import importlib.metadata as im

            im.version(package.split("[")[0].split(">")[0].split("=")[0].strip())
            return ToolStatus.AVAILABLE
        except Exception:
            return ToolStatus.NOT_FOUND

    def search(self, query: str) -> list[ToolDef]:
        q = query.lower()
        return [
            t
            for t in self._tools.values()
            if q in t.name.lower() or q in t.description.lower() or any(q in k.lower() for k in t.keywords)
        ]


_TOOL_REGISTRY: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _TOOL_REGISTRY
    if _TOOL_REGISTRY is None:
        _TOOL_REGISTRY = ToolRegistry()
    return _TOOL_REGISTRY
