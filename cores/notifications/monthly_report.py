"""Monthly Email Report — comprehensive monthly summary.

This module generates and sends a monthly email report containing:
- Income summary
- Opportunities detected/executed/discarded
- Time worked
- Income by source
- Main results
- Findings/reports
- Agent performance
- Automations executed
- Important errors
- Capital accumulated
- Progress towards goals
- Progress towards $1M
- Main learnings
- What worked/what didn't
- Recommendations for next month

The email should be written as a comprehensive report, not a technical dump.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cores.notifications.engine import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    get_notification_engine,
)

logger = logging.getLogger("ownex.notifications.monthly_report")


@dataclass
class MonthlyReportData:
    """Data for the monthly report."""

    # Period
    month: str  # "2026-08"
    year: int
    month_name: str  # "August"

    # Income
    total_income: float = 0.0
    income_by_source: dict[str, float] | None = None
    income_target: float = 0.0
    income_progress_pct: float = 0.0

    # Opportunities
    opportunities_detected: int = 0
    opportunities_executed: int = 0
    opportunities_discarded: int = 0
    opportunities_accepted: int = 0

    # Time
    time_worked_hours: float = 0.0
    time_by_activity: dict[str, float] | None = None

    # Results
    findings_count: int = 0
    reports_submitted: int = 0
    reports_accepted: int = 0
    total_payout: float = 0.0

    # Agents
    agent_tasks_completed: int = 0
    agent_success_rate: float = 0.0

    # Automations
    automations_executed: int = 0
    automations_successful: int = 0

    # Errors
    critical_errors: int = 0
    important_errors: int = 0

    # Capital
    capital_accumulated: float = 0.0
    capital_start: float = 0.0
    capital_change: float = 0.0

    # Goals
    goal_monthly_income: float = 0.0
    goal_progress_pct: float = 0.0
    goal_1m_progress_pct: float = 0.0
    goal_1m_projected_date: str = ""

    # Learnings
    what_worked: list[str] | None = None
    what_didnt_work: list[str] | None = None
    recommendations: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "month": self.month,
            "year": self.year,
            "month_name": self.month_name,
            "total_income": self.total_income,
            "income_by_source": self.income_by_source or {},
            "income_target": self.income_target,
            "income_progress_pct": self.income_progress_pct,
            "opportunities_detected": self.opportunities_detected,
            "opportunities_executed": self.opportunities_executed,
            "opportunities_discarded": self.opportunities_discarded,
            "opportunities_accepted": self.opportunities_accepted,
            "time_worked_hours": self.time_worked_hours,
            "time_by_activity": self.time_by_activity or {},
            "findings_count": self.findings_count,
            "reports_submitted": self.reports_submitted,
            "reports_accepted": self.reports_accepted,
            "total_payout": self.total_payout,
            "agent_tasks_completed": self.agent_tasks_completed,
            "agent_success_rate": self.agent_success_rate,
            "automations_executed": self.automations_executed,
            "automations_successful": self.automations_successful,
            "critical_errors": self.critical_errors,
            "important_errors": self.important_errors,
            "capital_accumulated": self.capital_accumulated,
            "capital_start": self.capital_start,
            "capital_change": self.capital_change,
            "goal_monthly_income": self.goal_monthly_income,
            "goal_progress_pct": self.goal_progress_pct,
            "goal_1m_progress_pct": self.goal_1m_progress_pct,
            "goal_1m_projected_date": self.goal_1m_projected_date,
            "what_worked": self.what_worked or [],
            "what_didnt_work": self.what_didnt_work or [],
            "recommendations": self.recommendations or [],
        }


class MonthlyReportEngine:
    """Generates and sends monthly email reports."""

    def __init__(self) -> None:
        self._engine = get_notification_engine()

    def generate_report(self, data: MonthlyReportData) -> str:
        """Generate the monthly report as HTML email."""

        # Build HTML email
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OWNEX Monthly Report - {data.month_name} {data.year}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .header p {{ margin: 8px 0 0; opacity: 0.9; font-size: 14px; }}
        .section {{ background: #f8f9fa; border-radius: 8px; padding: 20px; margin-bottom: 16px; }}
        .section h2 {{ margin: 0 0 12px; font-size: 16px; color: #667eea; }}
        .stat {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e9ecef; }}
        .stat:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #666; font-size: 14px; }}
        .stat-value {{ font-weight: 600; font-size: 14px; }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        .neutral {{ color: #6c757d; }}
        .progress-bar {{ background: #e9ecef; border-radius: 4px; height: 8px; margin-top: 8px; }}
        .progress-fill {{ background: #667eea; height: 100%; border-radius: 4px; }}
        .list-item {{ padding: 8px 0; border-bottom: 1px solid #e9ecef; font-size: 14px; }}
        .list-item:last-child {{ border-bottom: none; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
        .cta {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; margin-top: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 OWNEX Monthly Report</h1>
        <p>{data.month_name} {data.year}</p>
    </div>
    
    <div class="section">
        <h2>💰 Income Summary</h2>
        <div class="stat">
            <span class="stat-label">Total Income</span>
            <span class="stat-value">${data.total_income:,.2f}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Target</span>
            <span class="stat-value">${data.income_target:,.2f}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Progress</span>
            <span class="stat-value {"positive" if data.income_progress_pct >= 100 else "neutral"}">{data.income_progress_pct:.1f}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {min(data.income_progress_pct, 100)}%"></div>
        </div>
    </div>
    
    <div class="section">
        <h2>🎯 Opportunities</h2>
        <div class="stat">
            <span class="stat-label">Detected</span>
            <span class="stat-value">{data.opportunities_detected}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Executed</span>
            <span class="stat-value">{data.opportunities_executed}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Accepted</span>
            <span class="stat-value positive">{data.opportunities_accepted}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Discarded</span>
            <span class="stat-value neutral">{data.opportunities_discarded}</span>
        </div>
    </div>
    
    <div class="section">
        <h2>⏱️ Time Investment</h2>
        <div class="stat">
            <span class="stat-label">Total Hours</span>
            <span class="stat-value">{data.time_worked_hours:.1f}h</span>
        </div>
        <div class="stat">
            <span class="stat-label">EV/Hour</span>
            <span class="stat-value">${data.total_income / max(data.time_worked_hours, 1):,.2f}/h</span>
        </div>
    </div>
    
    <div class="section">
        <h2>📋 Results</h2>
        <div class="stat">
            <span class="stat-label">Findings</span>
            <span class="stat-value">{data.findings_count}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Reports Submitted</span>
            <span class="stat-value">{data.reports_submitted}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Reports Accepted</span>
            <span class="stat-value positive">{data.reports_accepted}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Total Payout</span>
            <span class="stat-value positive">${data.total_payout:,.2f}</span>
        </div>
    </div>
    
    <div class="section">
        <h2>🤖 Agents & Automation</h2>
        <div class="stat">
            <span class="stat-label">Agent Tasks Completed</span>
            <span class="stat-value">{data.agent_tasks_completed}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Agent Success Rate</span>
            <span class="stat-value">{data.agent_success_rate:.1%}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Automations Executed</span>
            <span class="stat-value">{data.automations_executed}</span>
        </div>
    </div>
    
    <div class="section">
        <h2>💼 Capital & Goals</h2>
        <div class="stat">
            <span class="stat-label">Capital Accumulated</span>
            <span class="stat-value">${data.capital_accumulated:,.2f}</span>
        </div>
        <div class="stat">
            <span class="stat-label">Monthly Change</span>
            <span class="stat-value {"positive" if data.capital_change >= 0 else "negative"}">${data.capital_change:+,.2f}</span>
        </div>
        <div class="stat">
            <span class="stat-label">$1M Progress</span>
            <span class="stat-value">{data.goal_1m_progress_pct:.1f}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {min(data.goal_1m_progress_pct, 100)}%"></div>
        </div>
        <div class="stat">
            <span class="stat-label">Projected $1M Date</span>
            <span class="stat-value">{data.goal_1m_projected_date or "N/A"}</span>
        </div>
    </div>
    
    <div class="section">
        <h2>📚 Learnings</h2>
        <h3 style="font-size: 14px; margin: 12px 0 8px; color: #28a745;">✅ What Worked</h3>
        {"".join(f'<div class="list-item">• {item}</div>' for item in (data.what_worked or []))}
        
        <h3 style="font-size: 14px; margin: 12px 0 8px; color: #dc3545;">❌ What Didn't Work</h3>
        {"".join(f'<div class="list-item">• {item}</div>' for item in (data.what_didnt_work or []))}
        
        <h3 style="font-size: 14px; margin: 12px 0 8px; color: #667eea;">💡 Recommendations</h3>
        {"".join(f'<div class="list-item">• {item}</div>' for item in (data.recommendations or []))}
    </div>
    
    <div class="footer">
        <p>Generated by OWNEX OMEGA</p>
        <p>{datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")}</p>
    </div>
</body>
</html>"""

        return html

    def send_monthly_report(self, data: MonthlyReportData, recipient_email: str) -> bool:
        """Send the monthly report via email."""

        # Generate HTML
        html = self.generate_report(data)

        # Create notification
        notification = Notification(
            type="monthly_report",
            title=f"📊 OWNEX Monthly Report - {data.month_name} {data.year}",
            message=f"Your monthly report is ready. Total income: ${data.total_income:,.2f}",
            priority=NotificationPriority.MEDIUM,
            severity="info",
            category=NotificationCategory.FINANCE,
            source="monthly_report_engine",
            source_id=data.month,
            channels=["email"],
            metadata={
                "report_data": data.to_dict(),
                "recipient_email": recipient_email,
                "html_content": html,
            },
        )

        # Send via engine
        result = self._engine.send(notification)

        if result:
            logger.info("Monthly report sent to %s", recipient_email)
            return True
        else:
            logger.warning("Failed to send monthly report to %s", recipient_email)
            return False

    def generate_and_store_report(self, data: MonthlyReportData) -> str:
        """Generate report and store it for later retrieval."""

        html = self.generate_report(data)

        # Store in notification engine
        notification = Notification(
            type="monthly_report",
            title=f"📊 OWNEX Monthly Report - {data.month_name} {data.year}",
            message="Your monthly report is ready.",
            priority=NotificationPriority.LOW,
            severity="info",
            category=NotificationCategory.FINANCE,
            source="monthly_report_engine",
            source_id=data.month,
            channels=["web"],
            metadata={
                "report_data": data.to_dict(),
                "html_content": html,
            },
        )

        self._engine.send(notification)

        return html


# Singleton instance
_monthly_report_engine: MonthlyReportEngine | None = None


def get_monthly_report_engine() -> MonthlyReportEngine:
    """Get or create the monthly report engine."""
    global _monthly_report_engine
    if _monthly_report_engine is None:
        _monthly_report_engine = MonthlyReportEngine()
    return _monthly_report_engine
