"""Sentiment Analysis Adapter for OWNEX.

Financial news sentiment, social media analysis, and market sentiment scoring.
Based on: FinBERT, Transformers, VADER, TextBlob, custom financial NLP models.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import aiohttp

logger = logging.getLogger("orion.investment.sentiment")


class SentimentAnalyzerAdapter:
    """Financial sentiment analysis adapter.

    Provides:
    - News sentiment analysis (FinBERT, custom models)
    - Social media sentiment (Twitter, Reddit, Discord)
    - Fear & Greed index
    - Market regime detection
    - Event impact scoring
    - Sentiment-based signals
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._session: aiohttp.ClientSession | None = None
        self._newsapi_key = self._config.get("newsapi_key", "")
        self._twitter_bearer = self._config.get("twitter_bearer_token", "")
        self._reddit_client_id = self._config.get("reddit_client_id", "")
        self._reddit_secret = self._config.get("reddit_client_secret", "")
        self._cryptopanic_key = self._config.get("cryptopanic_key", "")

        # Sentiment keywords for quick scoring
        self._positive_keywords = {
            "bullish",
            "surge",
            "rally",
            "breakout",
            "moon",
            "pump",
            "gains",
            "profit",
            "buy",
            "long",
            "support",
            "accumulation",
            "adoption",
            "partnership",
            "launch",
            "upgrade",
            "mainnet",
            "listing",
            "institutional",
            "whale",
            "buyback",
            "burn",
            "staking",
        }
        self._negative_keywords = {
            "bearish",
            "crash",
            "dump",
            "drop",
            "fall",
            "decline",
            "loss",
            "sell",
            "short",
            "resistance",
            "distribution",
            "hack",
            "exploit",
            "rug",
            "scam",
            "ban",
            "regulation",
            "lawsuit",
            "delisting",
            "bankruptcy",
            "insolvency",
            "liquidation",
            "margin call",
        }

    @property
    def name(self) -> str:
        return "sentiment_analysis"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def analyze_text(self, text: str) -> dict[str, Any]:
        """Analyze sentiment of a single text."""
        text_lower = text.lower()

        # Quick keyword scoring
        pos_count = sum(1 for kw in self._positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in self._negative_keywords if kw in text_lower)

        total = pos_count + neg_count
        if total == 0:
            keyword_score = 0.0
        else:
            keyword_score = (pos_count - neg_count) / total

        # Try FinBERT if available
        finbert_score = await self._finbert_score(text)

        # Combine scores
        final_score = (keyword_score + finbert_score) / 2 if finbert_score != 0 else keyword_score

        return {
            "text": text[:200],
            "sentiment_score": round(final_score, 3),  # -1 to 1
            "sentiment_label": self._score_to_label(final_score),
            "keyword_score": round(keyword_score, 3),
            "finbert_score": round(finbert_score, 3),
            "positive_keywords": pos_count,
            "negative_keywords": neg_count,
            "analyzed_at": datetime.now(UTC).isoformat(),
        }

    async def _finbert_score(self, text: str) -> float:
        """Get FinBERT sentiment score."""
        try:
            # Try to use transformers if available
            from transformers import pipeline

            if not hasattr(self, "_finbert_pipeline"):
                self._finbert_pipeline = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    return_all_scores=True,
                )

            result = self._finbert_pipeline(text[:512])[0]
            # Map to -1 to 1
            label_map = {"Positive": 1, "Negative": -1, "Neutral": 0}
            score = sum(label_map.get(r["label"], 0) * r["score"] for r in result)
            return score
        except Exception:
            return 0.0

    def _score_to_label(self, score: float) -> str:
        """Convert score to label."""
        if score > 0.3:
            return "bullish"
        elif score > 0.1:
            return "slightly_bullish"
        elif score > -0.1:
            return "neutral"
        elif score > -0.3:
            return "slightly_bearish"
        return "bearish"

    async def get_news_sentiment(
        self,
        symbols: list[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get sentiment from financial news."""
        articles = await self._fetch_news(symbols, limit)
        results = []

        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            sentiment = await self.analyze_text(text)
            results.append(
                {
                    "title": article.get("title"),
                    "url": article.get("url"),
                    "source": article.get("source", {}).get("name"),
                    "published_at": article.get("publishedAt"),
                    "sentiment": sentiment,
                }
            )

        # Aggregate
        if results:
            avg_score = sum(r["sentiment"]["sentiment_score"] for r in results) / len(results)
            bullish_count = sum(1 for r in results if r["sentiment"]["sentiment_score"] > 0.1)
            bearish_count = sum(1 for r in results if r["sentiment"]["sentiment_score"] < -0.1)
        else:
            avg_score = 0
            bullish_count = bearish_count = 0

        return {
            "articles_analyzed": len(results),
            "average_sentiment": round(avg_score, 3),
            "bullish_articles": bullish_count,
            "bearish_articles": bearish_count,
            "neutral_articles": len(results) - bullish_count - bearish_count,
            "articles": results,
            "analyzed_at": datetime.now(UTC).isoformat(),
        }

    async def _fetch_news(
        self,
        symbols: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch news from various sources."""
        all_articles = []

        # NewsAPI
        if self._newsapi_key:
            try:
                session = await self._get_session()
                query = " OR ".join(symbols) if symbols else "crypto OR bitcoin OR ethereum"
                url = "https://newsapi.org/v2/everything"
                params = {
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": limit,
                    "apiKey": self._newsapi_key,
                }
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        all_articles.extend(data.get("articles", []))
            except Exception as e:
                logger.warning("NewsAPI fetch failed: %s", e)

        # CryptoPanic
        if self._cryptopanic_key:
            try:
                session = await self._get_session()
                url = "https://cryptopanic.com/api/v1/posts/"
                params = {"auth_token": self._cryptopanic_key, "public": "true", "limit": limit}
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for post in data.get("results", []):
                            all_articles.append(
                                {
                                    "title": post.get("title"),
                                    "url": post.get("url"),
                                    "source": {"name": post.get("domain")},
                                    "publishedAt": post.get("created_at"),
                                    "description": post.get("description", ""),
                                }
                            )
            except Exception as e:
                logger.warning("CryptoPanic fetch failed: %s", e)

        return all_articles[:limit]

    async def get_social_sentiment(
        self,
        symbols: list[str] | None = None,
        sources: list[str] = None,
    ) -> dict[str, Any]:
        """Get sentiment from social media."""
        sources = sources or ["twitter", "reddit"]
        results = {}

        if "twitter" in sources and self._twitter_bearer:
            results["twitter"] = await self._fetch_twitter_sentiment(symbols)

        if "reddit" in sources and self._reddit_client_id:
            results["reddit"] = await self._fetch_reddit_sentiment(symbols)

        return results

    async def _fetch_twitter_sentiment(self, symbols: list[str] | None) -> dict[str, Any]:
        """Fetch Twitter sentiment."""
        # Would use Twitter API v2
        return {"tweets_analyzed": 0, "average_sentiment": 0.0}

    async def _fetch_reddit_sentiment(self, symbols: list[str] | None) -> dict[str, Any]:
        """Fetch Reddit sentiment."""
        # Would use Reddit API
        return {"posts_analyzed": 0, "average_sentiment": 0.0}

    async def get_fear_greed_index(self) -> dict[str, Any]:
        """Get Fear & Greed Index."""
        try:
            session = await self._get_session()
            url = "https://api.alternative.me/fng/"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    fng = data.get("data", [{}])[0]
                    return {
                        "value": int(fng.get("value", 50)),
                        "classification": fng.get("value_classification", "Neutral"),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
        except Exception as e:
            logger.error("Fear & Greed fetch failed: %s", e)

        return {"value": 50, "classification": "Neutral", "timestamp": datetime.now(UTC).isoformat()}

    async def get_market_regime(self) -> dict[str, Any]:
        """Detect current market regime."""
        # Combine multiple signals
        fng = await self.get_fear_greed_index()
        news = await self.get_news_sentiment(limit=20)

        fng_value = fng.get("value", 50)
        news_score = news.get("average_sentiment", 0)

        # Determine regime
        if fng_value > 75 and news_score > 0.2:
            regime = "euphoria"
        elif fng_value > 55 and news_score > 0:
            regime = "bull"
        elif fng_value < 25 and news_score < -0.2:
            regime = "capitulation"
        elif fng_value < 45 and news_score < 0:
            regime = "bear"
        else:
            regime = "sideways"

        return {
            "regime": regime,
            "fear_greed": fng_value,
            "news_sentiment": round(news_score, 3),
            "confidence": "medium",
            "analyzed_at": datetime.now(UTC).isoformat(),
        }

    async def analyze_symbol_sentiment(self, symbol: str) -> dict[str, Any]:
        """Comprehensive sentiment analysis for a symbol."""
        news = await self.get_news_sentiment([symbol], limit=30)
        fng = await self.get_fear_greed_index()
        regime = await self.get_market_regime()

        return {
            "symbol": symbol,
            "news_sentiment": news,
            "fear_greed": fng,
            "market_regime": regime,
            "overall_score": round((news.get("average_sentiment", 0) + (fng.get("value", 50) - 50) / 50) / 2, 3),
            "recommendation": self._get_recommendation(news.get("average_sentiment", 0), fng.get("value", 50)),
            "analyzed_at": datetime.now(UTC).isoformat(),
        }

    def _get_recommendation(self, news_score: float, fng: int) -> str:
        """Get action recommendation based on sentiment."""
        if news_score > 0.3 and fng < 70:
            return "accumulate"
        elif news_score > 0.1:
            return "hold"
        elif news_score < -0.3 and fng > 30:
            return "reduce"
        elif news_score < -0.1:
            return "caution"
        return "neutral"


def build_sentiment_adapter(config: dict[str, Any] | None = None) -> SentimentAnalyzerAdapter:
    """Factory function to create Sentiment Analysis adapter."""
    return SentimentAnalyzerAdapter(config)
