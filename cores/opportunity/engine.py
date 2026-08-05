"""
OWNEX Opportunity Engine — Initial version.

5 categories, 20 sources, filter, ranking, reward/time analysis.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from cores.ai.runtime import TaskType, get_oar
from cores.memory.system import MemoryNamespace, MemoryTier, get_memory_store

logger = logging.getLogger("ownex.opportunity")


class OpportunityCategory(str, Enum):
    # 1) Bug Bounty / Security Research
    BUG_BOUNTY = "bug_bounty"
    # 2) Dev Bounty / Desarrollo por recompensa
    DEV_BOUNTY = "dev_bounty"
    # 3) Freelance técnico sin proceso laboral tradicional
    FREELANCE_TECH = "freelance_tech"
    # 4) Data Annotation / AI Training
    DATA_ANNOTATION = "data_annotation"
    # 5) Microtasks / Human Intelligence Tasks
    MICROTASKS = "microtasks"
    # 6) Testing / QA / Software Evaluation
    TESTING_QA = "testing_qa"
    # 7) Open Source Contribution Rewards
    OPEN_SOURCE = "open_source"
    # 8) AI Evaluation / Model Testing
    AI_EVALUATION = "ai_evaluation"
    # 9) APIs / Developer Marketplaces
    API_MARKETPLACE = "api_marketplace"
    # 10) Creación y venta de productos digitales
    DIGITAL_PRODUCTS = "digital_products"
    # 11) Investigación, concursos y desafíos técnicos
    TECH_CHALLENGES = "tech_challenges"


class OpportunitySource(str, Enum):
    # 1) Bug Bounty / Security Research (1-10)
    HACKERONE = "hackerone"
    BUGCROWD = "bugcrowd"
    INTIGRITI = "intigriti"
    YESWEHACK = "yeswehack"
    OPEN_BUG_BOUNTY = "open_bug_bounty"
    HACKRATE = "hackrate"
    FEDERACY = "federacy"
    SYNACK = "synack"
    COBALT = "cobalt"
    SHERLOCK = "sherlock"

    # 2) Dev Bounty / Desarrollo por recompensa (11-20)
    ALGORA = "algora"
    GITCOIN = "gitcoin"
    ISSUEHUNT = "issuehunt"
    BOUNTYSOURCE = "bountysource"
    CODE4RENA = "code4rena"
    CODEHAWKS = "codehawks"
    SHERLOCK_DEV = "sherlock_dev"
    IMMUNEFI = "immunefi"
    ETHGLOBAL = "ethglobal"
    DEVPOST = "devpost"

    # 3) Freelance técnico (21-30)
    FIVERR = "fiverr"
    UPWORK = "upwork"
    FREELANCER_COM = "freelancer_com"
    PEOPLEPERHOUR = "peopleperhour"
    CONTRA = "contra"
    GURU = "guru"
    WORKNANA = "workana"
    TOPTAL = "toptal"
    ARC = "arc"
    GUN_IO = "gun_io"

    # 4) Data Annotation / AI Training (31-40)
    DATAANNOTATION = "dataannotation"
    OUTLIER = "outlier"
    SCALE_AI = "scale_ai"
    REMOTASKS = "remotasks"
    APPEN = "appen"
    TELUS_AI = "telus_ai"
    ONE_FORMA = "oneforma"
    CLICKWORKER = "clickworker"
    TOLOKA = "toloka"
    MICROWORKERS = "microworkers"

    # 5) Microtasks / HITs (41-50)
    MTURK = "mturk"
    PROLIFIC = "prolific"
    TASKVERSE = "taskverse"
    HIVE_MICRO = "hive_micro"
    REMOTASKS_2 = "remotasks_2"
    NEEVO = "neevo"
    TEST_IO = "test_io"
    USERTESTING = "usertesting"
    USERLYTICS = "userlytics"
    TRYMATA = "trymata"

    # 6) Testing / QA / Software Evaluation (51-60)
    UTEST = "utest"
    TESTLIO = "testlio"
    APPLAUSE = "applause"
    TESTBIRDS = "testbirds"
    BETAFAMILY = "betafamily"
    PLAYTESTCLOUD = "playtestcloud"
    FERPECTION = "ferpection"
    USERFEEL = "userfeel"
    RESPONDENT = "respondent"
    MAZE = "maze"

    # 7) Open Source Contribution Rewards (61-70)
    GITHUB_REWARDS = "github_rewards"
    GOOGLE_SUMMER_OF_CODE = "gsoc"
    MLH_FELLOWSHIP = "mlh_fellowship"
    OPEN_COLLECTIVE = "open_collective"
    POLAR = "polar"
    LFX_MENTORSHIP = "lfx_mentorship"
    CNCF_PROJECTS = "cncf_projects"
    MOZILLA_PROGRAMS = "mozilla_programs"
    APACHE_PROJECTS = "apache_projects"
    LINUX_FOUNDATION = "linux_foundation"

    # 8) AI Evaluation / Model Testing (71-80)
    SCALE_AI_EVAL = "scale_ai_eval"
    DATAFORCE = "dataforce"
    SURGE_AI = "surge_ai"
    ALIGNERR = "alignerr"
    MERCOR = "mercor"
    INVISIBLE_TECH = "invisible_tech"
    MINDDRIFT = "mindrift"
    RWS = "rws"
    WELOCALIZE = "welocalize"
    LXT = "lxt"

    # 9) APIs / Developer Marketplaces (81-90)
    RAPIDAPI = "rapidapi"
    AWS_MARKETPLACE = "aws_marketplace"
    VERCEL_MARKETPLACE = "vercel_marketplace"
    SHOPIFY_APP_STORE = "shopify_app_store"
    WORDPRESS_PLUGINS = "wordpress_plugins"
    CHROME_WEB_STORE = "chrome_web_store"
    FIREFOX_ADDONS = "firefox_addons"
    NPM = "npm"
    PYPI = "pypi"
    DOCKER_HUB = "docker_hub"

    # 10) Productos digitales (91-95)
    GUMROAD = "gumroad"
    LEMON_SQUEEZY = "lemon_squeezy"
    PADDLE = "paddle"
    KOFI = "kofi"
    BUY_ME_COFFEE = "buy_me_coffee"

    # 11) Investigación y desafíos técnicos (96-100)
    KAGGLE = "kaggle"
    HUGGINGFACE = "huggingface"
    DRIVENDATA = "drivendata"
    TOPCODER = "topcoder"
    CODEMENTOR = "codementor"
    ZAPIER = "zapier"
    MAKE = "make"


@dataclass
class Opportunity:
    id: str
    title: str
    description: str
    category: OpportunityCategory
    source: OpportunitySource
    url: str
    reward_min: float = 0.0
    reward_max: float = 0.0
    currency: str = "USD"
    estimated_hours: float = 0.0
    difficulty: str = "medium"  # easy, medium, hard, expert
    skills_required: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    posted_at: datetime | None = None
    deadline: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # OWNEX Daily Filter criteria (filtro principal)
    argentina_accessible: bool = True  # Acceso desde Argentina
    requires_interview: bool = False  # Requiere entrevista tradicional
    requires_portfolio: bool = False  # Requiere portfolio obligatorio
    requires_experience: bool = False  # Requiere experiencia previa obligatoria
    deliverable_based: bool = True  # Basado en resultados entregables
    clear_objectives: bool = True  # Objetivos claros y medibles
    automatable_pct: float = 0.0  # % que OWNEX puede automatizar (0-1)
    public_reward: bool = True  # Trabajo/recompensa pública
    global_access: bool = True  # Acceso global

    # Computed
    reward_per_hour: float = 0.0
    own_ex_score: float = 0.0  # OWNEX Score 0-100


@dataclass
class RankedOpportunity:
    opportunity: Opportunity
    score: float
    reward_per_hour: float
    match_score: float
    reasoning: str


class OpportunityFilter:
    """Filters opportunities based on OWNEX daily criteria."""

    def __init__(self):
        self.min_reward = 0.0
        self.max_hours = 100.0
        self.min_reward_per_hour = 5.0  # Mínimo $5/hora
        self.min_own_ex_score = 40.0  # Mínimo OWNEX score
        self.allowed_categories: list[OpportunityCategory] = list(OpportunityCategory)
        self.allowed_sources: list[OpportunitySource] = list(OpportunitySource)
        self.required_skills: list[str] = []
        self.excluded_keywords: list[str] = ["concurso", "eterno", "sorteo", "lotería", "rifa"]

        # OWNEX Daily Filter criteria (filtro principal)
        self.require_argentina_access = True
        self.reject_traditional_interview = True
        self.reject_mandatory_portfolio = True
        self.reject_mandatory_experience = True
        self.require_deliverable_based = True
        self.require_clear_objectives = True
        self.min_automation_pct = 0.0
        self.require_public_reward = True
        self.require_global_access = True

    def matches(self, opp: Opportunity) -> bool:
        # Basic filters
        if opp.reward_max < self.min_reward:
            return False
        if opp.estimated_hours > self.max_hours:
            return False
        if opp.category not in self.allowed_categories:
            return False
        if opp.source not in self.allowed_sources:
            return False
        if self.required_skills and not any(s in opp.skills_required for s in self.required_skills):
            return False
        if any(kw.lower() in opp.title.lower() for kw in self.excluded_keywords):
            return False

        # OWNEX Daily Filter - Filtro principal
        if self.require_argentina_access and not opp.argentina_accessible:
            return False
        if self.reject_traditional_interview and opp.requires_interview:
            return False
        if self.reject_mandatory_portfolio and opp.requires_portfolio:
            return False
        if self.reject_mandatory_experience and opp.requires_experience:
            return False
        if self.require_deliverable_based and not opp.deliverable_based:
            return False
        if self.require_clear_objectives and not opp.clear_objectives:
            return False
        if self.min_automation_pct > 0 and opp.automatable_pct < self.min_automation_pct:
            return False
        if self.require_public_reward and not opp.public_reward:
            return False
        if self.require_global_access and not opp.global_access:
            return False

        # Reward per hour filter
        if opp.estimated_hours > 0:
            rph = (opp.reward_min + opp.reward_max) / 2 / opp.estimated_hours
            if rph < self.min_reward_per_hour:
                return False

        # OWNEX score filter
        return not (opp.own_ex_score > 0 and opp.own_ex_score < self.min_own_ex_score)


class OpportunityRanker:
    """Ranks opportunities by OWNEX scoring: reward/hora, dificultad, automatización, objetivos claros."""

    def __init__(self):
        self.oar = get_oar()

        # Difficulty multipliers (lower difficulty = higher score)
        self.difficulty_multipliers = {
            "easy": 1.2,
            "medium": 1.0,
            "hard": 0.7,
            "expert": 0.5,
        }

    def calculate_reward_per_hour(self, opp: Opportunity) -> float:
        if opp.estimated_hours <= 0:
            return 0.0
        avg_reward = (opp.reward_min + opp.reward_max) / 2
        return avg_reward / opp.estimated_hours

    def calculate_own_ex_score(self, opp: Opportunity) -> float:
        """Calculate OWNEX Score 0-100 based on:
        - 30% Reward per hour (normalized)
        - 25% Difficulty (easier = higher)
        - 20% Automation potential (OWNEX can do %)
        - 15% Clear objectives
        - 10% Deliverable-based
        """
        score = 0.0

        # 1. Reward per hour (30%) - normalize to $100/hr = 1.0
        rph = self.calculate_reward_per_hour(opp)
        rph_score = min(rph / 100.0, 1.0)
        score += rph_score * 30

        # 2. Difficulty (25%) - easier = higher
        diff_mult = self.difficulty_multipliers.get(opp.difficulty, 1.0)
        score += diff_mult * 25

        # 3. Automation potential (20%) - OWNEX can automate
        score += opp.automatable_pct * 20

        # 4. Clear objectives (15%)
        score += 15 if opp.clear_objectives else 0

        # 5. Deliverable-based (10%)
        score += 10 if opp.deliverable_based else 0

        return min(score, 100.0)

    def calculate_match_score(
        self, opp: Opportunity, user_skills: list[str], user_preferences: dict[str, Any]
    ) -> float:
        score = 0.0

        # Skill match (40%)
        if opp.skills_required and user_skills:
            matches = sum(1 for s in opp.skills_required if s in user_skills)
            score += (matches / len(opp.skills_required)) * 0.4

        # Category preference (30%)
        preferred_cats = user_preferences.get("preferred_categories", [])
        if opp.category in preferred_cats:
            score += 0.3

        # Source preference (20%)
        preferred_sources = user_preferences.get("preferred_sources", [])
        if opp.source in preferred_sources:
            score += 0.2

        # Difficulty match (10%)
        preferred_diff = user_preferences.get("preferred_difficulty")
        if preferred_diff and opp.difficulty == preferred_diff:
            score += 0.1

        return min(score, 1.0)

    async def rank(
        self,
        opportunities: list[Opportunity],
        user_skills: list[str],
        user_preferences: dict[str, Any],
    ) -> list[RankedOpportunity]:
        ranked = []

        for opp in opportunities:
            # Calculate scores
            rph = self.calculate_reward_per_hour(opp)
            own_ex_score = self.calculate_own_ex_score(opp)
            opp.own_ex_score = own_ex_score  # Store for filter
            opp.reward_per_hour = rph

            match = self.calculate_match_score(opp, user_skills, user_preferences)

            # Combined score: 50% OWNEX score, 30% match, 20% RPH normalized
            combined = (own_ex_score / 100.0) * 0.5 + match * 0.3 + min(rph / 100.0, 1.0) * 0.2

            # Get AI reasoning for top candidates
            reasoning = ""
            if combined > 0.5:
                reasoning = await self._generate_reasoning(opp, rph, match, own_ex_score, user_skills)

            ranked.append(
                RankedOpportunity(
                    opportunity=opp,
                    score=combined,
                    reward_per_hour=rph,
                    match_score=match,
                    reasoning=reasoning,
                )
            )

        ranked.sort(key=lambda x: x.score, reverse=True)
        return ranked

    async def _generate_reasoning(
        self, opp: Opportunity, rph: float, match: float, own_ex_score: float, user_skills: list[str]
    ) -> str:
        prompt = f"""
Explain in 2 sentences why this opportunity is a good match for OWNEX:
Title: {opp.title}
Category: {opp.category}
Source: {opp.source}
Reward: ${opp.reward_min}-${opp.reward_max}
Hours: {opp.estimated_hours}
Reward/hour: ${rph:.2f}
OWNEX Score: {own_ex_score:.1f}/100
Match: {match:.2f}
User skills: {user_skills}
Required skills: {opp.skills_required}
Automation %: {opp.automatable_pct * 100:.0f}%
Difficulty: {opp.difficulty}
Clear objectives: {opp.clear_objectives}
Deliverable-based: {opp.deliverable_based}
"""
        response = await self.oar.chat(prompt, task_type=TaskType.REASONING, temperature=0.3, max_tokens=200)
        return response.content.strip()


class OpportunityEngine:
    """Main opportunity engine."""

    def __init__(self):
        self.filter = OpportunityFilter()
        self.ranker = OpportunityRanker()
        self._memory = None
        self._sources: dict[OpportunitySource, Any] = {}

    @property
    def memory(self):
        if self._memory is None:
            self._memory = get_memory_store()
        return self._memory

    def register_source(self, source: OpportunitySource, adapter: Any) -> None:
        """Register a source adapter."""
        self._sources[source] = adapter

    async def discover(self, sources: list[OpportunitySource] | None = None) -> list[Opportunity]:
        """Discover opportunities from registered sources."""
        sources = sources or list(self._sources.keys())
        all_opportunities = []

        for source in sources:
            adapter = self._sources.get(source)
            if adapter:
                try:
                    opps = await adapter.fetch_opportunities()
                    all_opportunities.extend(opps)
                except Exception as e:
                    logger.warning("Source %s failed: %s", source, e)

        return all_opportunities

    async def find_best(
        self,
        user_skills: list[str],
        user_preferences: dict[str, Any],
        limit: int = 10,
        sources: list[OpportunitySource] | None = None,
    ) -> list[RankedOpportunity]:
        """Find best opportunities for user."""

        # Discover
        opportunities = await self.discover(sources)

        # Filter
        filtered = [o for o in opportunities if self.filter.matches(o)]

        # Rank
        ranked = await self.ranker.rank(filtered, user_skills, user_preferences)

        # Store in memory for learning
        for ro in ranked[:limit]:
            self.memory.set(
                MemoryNamespace.OPPORTUNITIES,
                f"ranked_{ro.opportunity.id}",
                {
                    "opportunity_id": ro.opportunity.id,
                    "score": ro.score,
                    "reward_per_hour": ro.reward_per_hour,
                    "match_score": ro.match_score,
                    "reasoning": ro.reasoning,
                    "ranked_at": datetime.now(UTC).isoformat(),
                },
                tier=MemoryTier.PERMANENT,
                tags=["ranked", "opportunity"],
            )

        return ranked[:limit]

    def get_stats(self) -> dict[str, Any]:
        return {
            "registered_sources": len(self._sources),
            "filter_config": {
                "min_reward": self.filter.min_reward,
                "max_hours": self.filter.max_hours,
                "categories": [c.value for c in self.filter.allowed_categories],
            },
        }

    async def run_daily_pipeline(
        self,
        user_skills: list[str],
        user_preferences: dict[str, Any],
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Daily pipeline: crawler → filtro → score → top 10 → daily briefing

        Pipeline steps:
        1. CRAWLER: Discover opportunities from all registered sources
        2. FILTRO: Apply OWNEX daily filter (Argentina, no interview, no portfolio, etc.)
        3. SCORE: Calculate OWNEX Score + Match + RPH
        4. TOP 10: Select best opportunities
        5. BRIEFING: Generate daily briefing with reasoning
        """
        from datetime import UTC, datetime

        logger.info("Starting OWNEX daily opportunity pipeline")

        # 1. CRAWLER
        logger.info("Step 1/5: Crawling sources...")
        opportunities = await self.discover()
        logger.info(f"  Discovered {len(opportunities)} raw opportunities")

        # 2. FILTRO - Apply OWNEX daily filter
        logger.info("Step 2/5: Applying OWNEX daily filter...")
        filtered = [o for o in opportunities if self.filter.matches(o)]
        logger.info(f"  Passed filter: {len(filtered)} / {len(opportunities)}")

        rejected_count = len(opportunities) - len(filtered)
        if rejected_count > 0:
            logger.info(f"  Rejected: {rejected_count} (interview, portfolio, no Argentina access, etc.)")

        # 3. SCORE - Calculate OWNEX Score + Match + RPH
        logger.info("Step 3/5: Scoring opportunities...")
        ranked = await self.ranker.rank(filtered, user_skills, user_preferences)
        logger.info(f"  Scored {len(ranked)} opportunities")

        # 4. TOP 10
        logger.info("Step 4/5: Selecting top opportunities...")
        top_opportunities = ranked[:limit]

        # 5. BRIEFING - Generate daily briefing
        logger.info("Step 5/5: Generating daily briefing...")
        briefing = self._generate_daily_briefing(top_opportunities, user_skills, user_preferences)

        # Store in memory
        briefing_id = f"daily_{datetime.now(UTC).date().isoformat()}"
        self.memory.set(
            MemoryNamespace.OPPORTUNITIES,
            briefing_id,
            {
                "date": datetime.now(UTC).date().isoformat(),
                "total_discovered": len(opportunities),
                "filtered_count": len(filtered),
                "rejected_count": rejected_count,
                "top_opportunities": [
                    {
                        "id": ro.opportunity.id,
                        "title": ro.opportunity.title,
                        "category": ro.opportunity.category.value,
                        "source": ro.opportunity.source.value,
                        "score": ro.score,
                        "reward_per_hour": ro.reward_per_hour,
                        "own_ex_score": ro.opportunity.own_ex_score,
                        "reward_range": f"${ro.opportunity.reward_min}-${ro.opportunity.reward_max}",
                        "hours": ro.opportunity.estimated_hours,
                        "difficulty": ro.opportunity.difficulty,
                        "automation_pct": ro.opportunity.automatable_pct,
                        "reasoning": ro.reasoning,
                    }
                    for ro in top_opportunities
                ],
                "briefing": briefing,
                "generated_at": datetime.now(UTC).isoformat(),
            },
            tier=MemoryTier.PERMANENT,
            tags=["daily_briefing", "pipeline"],
        )

        return {
            "pipeline_id": briefing_id,
            "date": datetime.now(UTC).date().isoformat(),
            "stats": {
                "total_discovered": len(opportunities),
                "passed_filter": len(filtered),
                "rejected": rejected_count,
                "top_selected": len(top_opportunities),
            },
            "top_opportunities": top_opportunities,
            "briefing": briefing,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _generate_daily_briefing(
        self,
        top_opportunities: list,
        user_skills: list[str],
        user_preferences: dict[str, Any],
    ) -> str:
        """Generate human-readable daily briefing."""
        if not top_opportunities:
            return "📭 No opportunities passed the OWNEX filter today. Consider adjusting criteria or checking new sources."

        lines = [
            "🌅 **OWNEX Daily Opportunity Briefing**",
            f"📅 {datetime.now(UTC).strftime('%Y-%m-%d')}",
            "",
            f"🎯 **Top {len(top_opportunities)} oportunidades filtradas por OWNEX:**",
            "",
        ]

        for i, ro in enumerate(top_opportunities, 1):
            opp = ro.opportunity
            lines.append(f"{i}. **{opp.title}** ({opp.category.value})")
            lines.append(
                f"   💰 ${opp.reward_min}-${opp.reward_max} | ⏱️ {opp.estimated_hours}h | "
                f"💵 ${ro.reward_per_hour:.0f}/hr | 🎯 OWNEX: {opp.own_ex_score:.0f}/100"
            )
            lines.append(f"   🤖 Automatizable: {opp.automatable_pct * 100:.0f}% | 📊 Dificultad: {opp.difficulty}")
            if ro.reasoning:
                lines.append(f"   💡 {ro.reasoning}")
            lines.append("")

        # Summary stats
        avg_rph = sum(ro.reward_per_hour for ro in top_opportunities) / len(top_opportunities)
        avg_own_ex = sum(ro.opportunity.own_ex_score for ro in top_opportunities) / len(top_opportunities)
        total_hours = sum(ro.opportunity.estimated_hours for ro in top_opportunities)
        total_reward = sum((ro.opportunity.reward_min + ro.opportunity.reward_max) / 2 for ro in top_opportunities)

        lines.extend(
            [
                "📊 **Resumen del día:**",
                f"   • Recompensa promedio/hora: ${avg_rph:.0f}",
                f"   • OWNEX Score promedio: {avg_own_ex:.0f}/100",
                f"   • Horas totales estimadas: {total_hours:.0f}h",
                f"   • Recompensa total potencial: ${total_reward:.0f}",
                "",
                "🚀 **Próximos pasos:** Revisar top 3, preparar entregables, ejecutar con OWNEX.",
            ]
        )

        return "\n".join(lines)


# Pre-seeded opportunities for testing
SEED_OPPORTUNITIES = [
    Opportunity(
        id="h1_001",
        title="IDOR in User Profile API",
        description="Insecure Direct Object Reference allowing access to other users' profiles",
        category=OpportunityCategory.BUG_BOUNTY,
        source=OpportunitySource.HACKERONE,
        url="https://hackerone.com/reports/123456",
        reward_min=500,
        reward_max=2000,
        estimated_hours=4,
        difficulty="medium",
        skills_required=["api_testing", "authorization", "burp_suite"],
        tags=["idor", "api", "authorization"],
    ),
    Opportunity(
        id="gh_001",
        title="React Component Library Bug Fix",
        description="Fix rendering issue in open-source component library",
        category=OpportunityCategory.DEV_BOUNTY,
        source=OpportunitySource.GITHUB_REWARDS,
        url="https://github.com/org/repo/issues/789",
        reward_min=200,
        reward_max=500,
        estimated_hours=3,
        difficulty="easy",
        skills_required=["react", "typescript", "testing"],
        tags=["react", "frontend", "open_source"],
    ),
    Opportunity(
        id="kc_001",
        title="Customer Churn Prediction",
        description="Build ML model to predict customer churn from transaction data",
        category=OpportunityCategory.DATA_ANNOTATION,
        source=OpportunitySource.KAGGLE,
        url="https://kaggle.com/competitions/churn-prediction",
        reward_min=1000,
        reward_max=5000,
        estimated_hours=20,
        difficulty="hard",
        skills_required=["python", "pandas", "sklearn", "xgboost", "mlops"],
        tags=["ml", "classification", "customer_analytics"],
    ),
    Opportunity(
        id="zp_001",
        title="Automate Lead Enrichment Workflow",
        description="Create Zapier workflow to enrich leads from webhook data",
        category=OpportunityCategory.TECH_CHALLENGES,
        source=OpportunitySource.ZAPIER,
        url="https://zapier.com/experts/jobs/123",
        reward_min=150,
        reward_max=400,
        estimated_hours=2,
        difficulty="easy",
        skills_required=["zapier", "webhooks", "api_integration"],
        tags=["automation", "no_code", "lead_gen"],
    ),
    Opportunity(
        id="im_001",
        title="Smart Contract Reentrancy Audit",
        description="Audit DeFi protocol for reentrancy vulnerabilities",
        category=OpportunityCategory.BUG_BOUNTY,
        source=OpportunitySource.IMMUNEFI,
        url="https://immunefi.com/bounty/defi-protocol",
        reward_min=10000,
        reward_max=50000,
        estimated_hours=40,
        difficulty="expert",
        skills_required=["solidity", "smart_contracts", "auditing", "foundry"],
        tags=["defi", "reentrancy", "web3", "audit"],
    ),
]


# Backward compatibility - provide get_engine as alias for get_opportunity_engine
def get_engine():
    """Backward compatibility alias for get_opportunity_engine."""
    from cores.opportunity.engine import get_opportunity_engine

    return get_opportunity_engine()


_opportunity_engine: OpportunityEngine | None = None


def get_opportunity_engine() -> OpportunityEngine:
    global _opportunity_engine
    if _opportunity_engine is None:
        _opportunity_engine = OpportunityEngine()
        # Seed with test opportunities
        for opp in SEED_OPPORTUNITIES:
            _opportunity_engine.memory.set(
                MemoryNamespace.OPPORTUNITIES,
                f"seed_{opp.id}",
                {
                    "id": opp.id,
                    "title": opp.title,
                    "category": opp.category.value,
                    "source": opp.source.value,
                    "reward_min": opp.reward_min,
                    "reward_max": opp.reward_max,
                    "estimated_hours": opp.estimated_hours,
                    "difficulty": opp.difficulty,
                    "skills_required": opp.skills_required,
                },
                tier=MemoryTier.PERMANENT,
                tags=["seed", "opportunity"],
            )
    return _opportunity_engine


async def find_opportunities(
    user_skills: list[str],
    user_preferences: dict[str, Any] | None = None,
    limit: int = 10,
) -> list[RankedOpportunity]:
    """Quick function to find opportunities."""
    engine = get_opportunity_engine()
    return await engine.find_best(user_skills, user_preferences or {}, limit)
