#!/usr/bin/env python3
"""
OWNEX Demo Screenshot Generator
Creates high-quality SVG demos for each product section
"""

from pathlib import Path


def generate_mission_control_demo():
    """Mission Control dashboard demo"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#111115;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="card-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1A1A1A;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="1920" height="1080" fill="url(#bg-gradient)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1920" height="80" fill="#0B0B0B" stroke="#1A1A1A" stroke-width="1"/>
  <text x="40" y="50" font-family="Inter, sans-serif" font-size="24" font-weight="700" fill="#FFFFFF">Mission Control</text>
  <circle cx="1850" cy="40" r="20" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="1850" cy="40" r="12" fill="#2D7FF9"/>

  <!-- Metric Cards Row 1 -->
  <g transform="translate(40, 120)">
    <rect width="400" height="150" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Active Opportunities</text>
    <text x="20" y="90" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#2D7FF9">247</text>
    <text x="20" y="120" font-family="Inter, sans-serif" font-size="12" fill="#00C853">↑ 12% this week</text>
  </g>

  <g transform="translate(480, 120)">
    <rect width="400" height="150" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Work Bank Ready</text>
    <text x="20" y="90" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#2D7FF9">89</text>
    <text x="20" y="120" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Target: 100/day</text>
  </g>

  <g transform="translate(920, 120)">
    <rect width="400" height="150" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Revenue This Month</text>
    <text x="20" y="90" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#D4AF37">$12,450</text>
    <text x="20" y="120" font-family="Inter, sans-serif" font-size="12" fill="#00C853">↑ 23% vs last month</text>
  </g>

  <g transform="translate(1360, 120)">
    <rect width="400" height="150" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Active Agents</text>
    <text x="20" y="90" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#2D7FF9">6</text>
    <text x="20" y="120" font-family="Inter, sans-serif" font-size="12" fill="#00C853">All systems operational</text>
  </g>

  <!-- Main Dashboard Area -->
  <rect x="40" y="300" width="1200" height="400" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="60" y="340" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Opportunity Queue</text>

  <!-- Opportunity List Items -->
  <g transform="translate(60, 380)">
    <rect width="1160" height="60" rx="8" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1" opacity="0.3"/>
    <circle cx="30" cy="30" r="8" fill="#2D7FF9"/>
    <text x="50" y="25" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF">HackerOne - SQL Injection</text>
    <text x="50" y="45" font-family="Inter, sans-serif" font-size="12" fill="#888888">Zero-barrier score: 87 · Priority: HIGH</text>
    <rect x="1000" y="20" width="100" height="20" rx="4" fill="#00C853"/>
    <text x="1040" y="35" font-family="Inter, sans-serif" font-size="11" fill="#FFFFFF">READY</text>
  </g>

  <g transform="translate(60, 460)">
    <rect width="1160" height="60" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <circle cx="30" cy="30" r="8" fill="#FFAB00"/>
    <text x="50" y="25" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF">Bugcrowd - XSS</text>
    <text x="50" y="45" font-family="Inter, sans-serif" font-size="12" fill="#888888">Zero-barrier score: 72 · Priority: MEDIUM</text>
    <rect x="1000" y="20" width="100" height="20" rx="4" fill="#FFAB00"/>
    <text x="1020" y="35" font-family="Inter, sans-serif" font-size="11" fill="#FFFFFF">ANALYZING</text>
  </g>

  <g transform="translate(60, 540)">
    <rect width="1160" height="60" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <circle cx="30" cy="30" r="8" fill="#2D7FF9"/>
    <text x="50" y="25" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF">Intigriti - IDOR</text>
    <text x="50" y="45" font-family="Inter, sans-serif" font-size="12" fill="#888888">Zero-barrier score: 91 · Priority: HIGH</text>
    <rect x="1000" y="20" width="100" height="20" rx="4" fill="#00C853"/>
    <text x="1040" y="35" font-family="Inter, sans-serif" font-size="11" fill="#FFFFFF">READY</text>
  </g>

  <g transform="translate(60, 620)">
    <rect width="1160" height="60" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <circle cx="30" cy="30" r="8" fill="#2D7FF9"/>
    <text x="50" y="25" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="#FFFFFF">YesWeHack - RCE</text>
    <text x="50" y="45" font-family="Inter, sans-serif" font-size="12" fill="#888888">Zero-barrier score: 84 · Priority: HIGH</text>
    <rect x="1000" y="20" width="100" height="20" rx="4" fill="#00C853"/>
    <text x="1040" y="35" font-family="Inter, sans-serif" font-size="11" fill="#FFFFFF">READY</text>
  </g>

  <!-- Side Panel -->
  <rect x="1280" y="300" width="600" height="400" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="1300" y="340" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Active Work Cycles</text>

  <g transform="translate(1300, 380)">
    <rect width="560" height="50" rx="8" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1" opacity="0.3"/>
    <text x="20" y="32" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">🔵 Security Cycle</text>
    <text x="400" y="32" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Running</text>
  </g>

  <g transform="translate(1300, 450)">
    <rect width="560" height="50" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="32" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">🛠️ Forge Cycle</text>
    <text x="400" y="32" font-family="Inter, sans-serif" font-size="12" fill="#888888">Idle</text>
  </g>

  <g transform="translate(1300, 520)">
    <rect width="560" height="50" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="32" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">💰 Vault Cycle</text>
    <text x="400" y="32" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Running</text>
  </g>

  <g transform="translate(1300, 590)">
    <rect width="560" height="50" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="32" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">🗺️ Atlas Cycle</text>
    <text x="400" y="32" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Running</text>
  </g>

  <!-- Footer Stats -->
  <rect x="40" y="740" width="1840" height="300" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="60" y="780" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">System Health</text>

  <g transform="translate(60, 820)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Backend Status</text>
    <rect x="0" y="10" width="200" height="8" rx="4" fill="#00C853"/>
    <text x="210" y="20" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Operational</text>
  </g>

  <g transform="translate(60, 880)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Frontend Status</text>
    <rect x="0" y="10" width="200" height="8" rx="4" fill="#00C853"/>
    <text x="210" y="20" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Operational</text>
  </g>

  <g transform="translate(60, 940)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Database Status</text>
    <rect x="0" y="10" width="200" height="8" rx="4" fill="#00C853"/>
    <text x="210" y="20" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Connected</text>
  </g>

  <g transform="translate(400, 820)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">AI Runtime</text>
    <rect x="0" y="10" width="200" height="8" rx="4" fill="#00C853"/>
    <text x="210" y="20" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Ollama Active</text>
  </g>

  <g transform="translate(400, 880)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Scheduler</text>
    <rect x="0" y="10" width="200" height="8" rx="4" fill="#00C853"/>
    <text x="210" y="20" font-family="Inter, sans-serif" font-size="12" fill="#00C853">28 Jobs Running</text>
  </g>

  <g transform="translate(400, 940)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">EventBus</text>
    <rect x="0" y="10" width="200" height="8" rx="4" fill="#00C853"/>
    <text x="210" y="20" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Connected</text>
  </g>
</svg>"""
    return svg


def generate_intelligence_demo():
    """Intelligence demo with data analysis"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#111115;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="card-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1A1A1A;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>
  </defs>

  <rect width="1920" height="1080" fill="url(#bg-gradient)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1920" height="80" fill="#0B0B0B" stroke="#1A1A1A" stroke-width="1"/>
  <text x="40" y="50" font-family="Inter, sans-serif" font-size="24" font-weight="700" fill="#FFFFFF">Intelligence</text>
  <circle cx="1850" cy="40" r="20" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="1850" cy="40" r="12" fill="#2D7FF9"/>

  <!-- Main Content -->
  <rect x="40" y="120" width="1200" height="880" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="60" y="160" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Opportunity Analysis</text>

  <!-- Analysis Cards -->
  <g transform="translate(60, 200)">
    <rect width="1080" height="120" rx="8" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1" opacity="0.2"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">Top Platform This Week</text>
    <text x="20" y="70" font-family="Inter, sans-serif" font-size="32" font-weight="700" fill="#2D7FF9">HackerOne</text>
    <text x="300" y="70" font-family="Inter, sans-serif" font-size="16" fill="#FFFFFF">45 opportunities · 87 avg score</text>
    <text x="20" y="100" font-family="Inter, sans-serif" font-size="12" fill="#00C853">↑ 18% increase</text>
  </g>

  <g transform="translate(60, 340)">
    <rect width="1080" height="120" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">Zero-Barrier Success Rate</text>
    <text x="20" y="70" font-family="Inter, sans-serif" font-size="32" font-weight="700" fill="#D4AF37">34%</text>
    <text x="150" y="70" font-family="Inter, sans-serif" font-size="16" fill="#FFFFFF">of opportunities bypass gates</text>
    <text x="20" y="100" font-family="Inter, sans-serif" font-size="12" fill="#00C853">↑ 5% this month</text>
  </g>

  <g transform="translate(60, 480)">
    <rect width="1080" height="120" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">Average Response Time</text>
    <text x="20" y="70" font-family="Inter, sans-serif" font-size="32" font-weight="700" fill="#2D7FF9">2.4 hours</text>
    <text x="200" y="70" font-family="Inter, sans-serif" font-size="16" fill="#FFFFFF">from discovery to report</text>
    <text x="20" y="100" font-family="Inter, sans-serif" font-size="12" fill="#00C853">↓ 18% improvement</text>
  </g>

  <!-- Chart Area -->
  <rect x="60" y="620" width="500" height="350" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
  <text x="80" y="660" font-family="Inter, sans-serif" font-size="14" fill="#888888">Weekly Opportunity Flow</text>
  
  <!-- Simple bar chart -->
  <rect x="80" y="720" width="60" height="200" fill="#2D7FF9" opacity="0.8"/>
  <rect x="160" y="680" width="60" height="240" fill="#2D7FF9" opacity="0.8"/>
  <rect x="240" y="750" width="60" height="170" fill="#2D7FF9" opacity="0.8"/>
  <rect x="320" y="700" width="60" height="220" fill="#2D7FF9" opacity="0.8"/>
  <rect x="400" y="650" width="60" height="270" fill="#2D7FF9" opacity="0.8"/>
  <rect x="480" y="600" width="60" height="320" fill="#2D7FF9" opacity="0.8"/>
  
  <text x="80" y="940" font-family="Inter, sans-serif" font-size="10" fill="#888888">Mon</text>
  <text x="160" y="940" font-family="Inter, sans-serif" font-size="10" fill="#888888">Tue</text>
  <text x="240" y="940" font-family="Inter, sans-serif" font-size="10" fill="#888888">Wed</text>
  <text x="320" y="940" font-family="Inter, sans-serif" font-size="10" fill="#888888">Thu</text>
  <text x="400" y="940" font-family="Inter, sans-serif" font-size="10" fill="#888888">Fri</text>
  <text x="480" y="940" font-family="Inter, sans-serif" font-size="10" fill="#888888">Sat</text>

  <!-- Side Panel -->
  <rect x="1280" y="120" width="600" height="880" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="1300" y="160" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Intelligence Insights</text>

  <g transform="translate(1300, 200)">
    <rect width="560" height="80" rx="8" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1" opacity="0.2"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">HackerOne</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#00C853">High success rate, good payouts</text>
  </g>

  <g transform="translate(1300, 300)">
    <rect width="560" height="80" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">Bugcrowd</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#FFAB00">Moderate competition</text>
  </g>

  <g transform="translate(1300, 400)">
    <rect width="560" height="80" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">Intigriti</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#00C853">High-value targets</text>
  </g>

  <g transform="translate(1300, 500)">
    <rect width="560" height="80" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">YesWeHack</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Fast response times</text>
  </g>

  <g transform="translate(1300, 600)">
    <rect width="560" height="80" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">Synack</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#FFAB00">Invite-only, slow access</text>
  </g>

  <g transform="translate(1300, 700)">
    <rect width="560" height="80" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">Immunefi</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#FF1744">DeFi focus, low bounty</text>
  </g>

  <g transform="translate(1300, 800)">
    <rect width="560" height="80" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#888888">Recommendation</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#2D7FF9">Focus on HackerOne + Intigriti</text>
  </g>
</svg>"""
    return svg


def generate_targets_demo():
    """Targets demo with prioritization"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#111115;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="card-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1A1A1A;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>
  </defs>

  <rect width="1920" height="1080" fill="url(#bg-gradient)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1920" height="80" fill="#0B0B0B" stroke="#1A1A1A" stroke-width="1"/>
  <text x="40" y="50" font-family="Inter, sans-serif" font-size="24" font-weight="700" fill="#FFFFFF">Targets</text>
  <circle cx="1850" cy="40" r="20" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="1850" cy="40" r="12" fill="#2D7FF9"/>

  <!-- Filter Bar -->
  <rect x="40" y="120" width="1840" height="60" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
  <text x="60" y="158" font-family="Inter, sans-serif" font-size="14" fill="#888888">Filter: All Platforms</text>
  <text x="300" y="158" font-family="Inter, sans-serif" font-size="14" fill="#2D7FF9">HackerOne</text>
  <text x="420" y="158" font-family="Inter, sans-serif" font-size="14" fill="#888888">Bugcrowd</text>
  <text x="540" y="158" font-family="Inter, sans-serif" font-size="14" fill="#888888">Intigriti</text>
  <rect x="1700" y="135" width="120" height="30" rx="4" fill="#2D7FF9"/>
  <text x="1720" y="155" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">Add Target</text>

  <!-- Target List -->
  <g transform="translate(40, 200)">
    <rect width="1840" height="100" rx="8" fill="url(#card-gradient)" stroke="#2D7FF9" stroke-width="1" opacity="0.3"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">HackerOne - Tesla Motors</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">Program: Tesla Motors · Zero-barrier: 89 · Payout: $50,000</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#00C853"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ACTIVE</text>
    <rect x="1650" y="25" width="120" height="30" rx="4" fill="#2D7FF9"/>
    <text x="1670" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">HIGH PRIORITY</text>
  </g>

  <g transform="translate(40, 320)">
    <rect width="1840" height="100" rx="8" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">HackerOne - Uber Technologies</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">Program: Uber Technologies · Zero-barrier: 85 · Payout: $100,000</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#00C853"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ACTIVE</text>
    <rect x="1650" y="25" width="120" height="30" rx="4" fill="#2D7FF9"/>
    <text x="1670" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">HIGH PRIORITY</text>
  </g>

  <g transform="translate(40, 440)">
    <rect width="1840" height="100" rx="8" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">Intigriti - Air France</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">Program: Air France · Zero-barrier: 91 · Payout: €25,000</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#00C853"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ACTIVE</text>
    <rect x="1650" y="25" width="120" height="30" rx="4" fill="#2D7FF9"/>
    <text x="1670" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">HIGH PRIORITY</text>
  </g>

  <g transform="translate(40, 560)">
    <rect width="1840" height="100" rx="8" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">Bugcrowd - Shopify</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">Program: Shopify · Zero-barrier: 72 · Payout: $15,000</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#FFAB00"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">PAUSED</text>
    <rect x="1650" y="25" width="120" height="30" rx="4" fill="#888888"/>
    <text x="1670" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">MEDIUM</text>
  </g>

  <g transform="translate(40, 680)">
    <rect width="1840" height="100" rx="8" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">YesWeHack - GitLab</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">Program: GitLab · Zero-barrier: 78 · Payout: $20,000</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#00C853"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ACTIVE</text>
    <rect x="1650" y="25" width="120" height="30" rx="4" fill="#888888"/>
    <text x="1670" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">MEDIUM</text>
  </g>

  <g transform="translate(40, 800)">
    <rect width="1840" height="100" rx="8" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">YesWeHack - Mozilla</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">Program: Mozilla · Zero-barrier: 82 · Payout: $30,000</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#00C853"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ACTIVE</text>
    <rect x="1650" y="25" width="120" height="30" rx="4" fill="#888888"/>
    <text x="1670" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">MEDIUM</text>
  </g>

  <!-- Stats Panel -->
  <rect x="40" y="920" width="1840" height="120" rx="8" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="60" y="960" font-family="Inter, sans-serif" font-size="14" fill="#888888">Total Targets: 156</text>
  <text x="250" y="960" font-family="Inter, sans-serif" font-size="14" fill="#00C853">Active: 24</text>
  <text x="400" y="960" font-family="Inter, sans-serif" font-size="14" fill="#FFAB00">Paused: 8</text>
  <text x="550" y="960" font-family="Inter, sans-serif" font-size="14" fill="#888888">Avg Zero-barrier: 78</text>
  <text x="750" y="960" font-family="Inter, sans-serif" font-size="14" fill="#D4AF37">Est. Monthly: $48,000</text>
</svg>"""
    return svg


def generate_capital_demo():
    """Capital demo with financial dashboard"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#111115;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="card-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1A1A1A;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>
  </defs>

  <rect width="1920" height="1080" fill="url(#bg-gradient)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1920" height="80" fill="#0B0B0B" stroke="#1A1A1A" stroke-width="1"/>
  <text x="40" y="50" font-family="Inter, sans-serif" font-size="24" font-weight="700" fill="#FFFFFF">Capital</text>
  <circle cx="1850" cy="40" r="20" fill="#D4AF37" opacity="0.3"/>
  <circle cx="1850" cy="40" r="12" fill="#D4AF37"/>

  <!-- Revenue Cards -->
  <g transform="translate(40, 120)">
    <rect width="400" height="180" rx="12" fill="url(#card-gradient)" stroke="#D4AF37" stroke-width="1" opacity="0.3"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Total Revenue (YTD)</text>
    <text x="20" y="100" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#D4AF37">$127,450</text>
    <text x="20" y="140" font-family="Inter, sans-serif" font-size="12" fill="#00C853">↑ 34% vs last year</text>
  </g>

  <g transform="translate(480, 120)">
    <rect width="400" height="180" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">This Month</text>
    <text x="20" y="100" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#2D7FF9">$12,450</text>
    <text x="20" y="140" font-family="Inter, sans-serif" font-size="12" fill="#00C853">↑ 23% vs last month</text>
  </g>

  <g transform="translate(920, 120)">
    <rect width="400" height="180" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Pending Payouts</text>
    <text x="20" y="100" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#FFAB00">$8,200</text>
    <text x="20" y="140" font-family="Inter, sans-serif" font-size="12" fill="#888888">3 reports awaiting review</text>
  </g>

  <g transform="translate(1360, 120)">
    <rect width="400" height="180" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Work Bank Value</text>
    <text x="20" y="100" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#2D7FF9">$45,000</text>
    <text x="20" y="140" font-family="Inter, sans-serif" font-size="12" fill="#00C853">89 ready jobs</text>
  </g>

  <!-- Revenue Chart -->
  <rect x="40" y="340" width="1200" height="400" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="60" y="380" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Revenue Timeline</text>

  <!-- Bar chart -->
  <rect x="60" y="420" width="80" height="280" fill="#2D7FF9" opacity="0.8"/>
  <rect x="160" y="380" width="80" height="320" fill="#2D7FF9" opacity="0.8"/>
  <rect x="260" y="440" width="80" height="260" fill="#2D7FF9" opacity="0.8"/>
  <rect x="360" y="400" width="80" height="300" fill="#2D7FF9" opacity="0.8"/>
  <rect x="460" y="350" width="80" height="350" fill="#2D7FF9" opacity="0.8"/>
  <rect x="560" y="320" width="80" height="380" fill="#2D7FF9" opacity="0.8"/>
  <rect x="660" y="380" width="80" height="320" fill="#2D7FF9" opacity="0.8"/>
  <rect x="760" y="400" width="80" height="300" fill="#2D7FF9" opacity="0.8"/>
  <rect x="860" y="360" width="80" height="340" fill="#2D7FF9" opacity="0.8"/>
  <rect x="960" y="420" width="80" height="280" fill="#2D7FF9" opacity="0.8"/>
  <rect x="1060" y="380" width="80" height="320" fill="#2D7FF9" opacity="0.8"/>

  <text x="60" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Jan</text>
  <text x="160" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Feb</text>
  <text x="260" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Mar</text>
  <text x="360" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Apr</text>
  <text x="460" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">May</text>
  <text x="560" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Jun</text>
  <text x="660" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Jul</text>
  <text x="760" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Aug</text>
  <text x="860" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Sep</text>
  <text x="960" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Oct</text>
  <text x="1060" y="720" font-family="Inter, sans-serif" font-size="10" fill="#888888">Nov</text>

  <!-- Transactions -->
  <rect x="1280" y="340" width="600" height="400" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="1300" y="380" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Recent Transactions</text>

  <g transform="translate(1300, 420)">
    <rect width="560" height="50" rx="8" fill="#1A1A1A" stroke="#00C853" stroke-width="1" opacity="0.2"/>
    <text x="20" y="32" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">HackerOne - Tesla · $50,000</text>
    <text x="400" y="32" font-family="Inter, sans-serif" font-size="12" fill="#00C853">2 days ago</text>
  </g>

  <g transform="translate(1300, 490)">
    <rect width="560" height="50" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="32" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Intigriti - Air France · €25,000</text>
    <text x="400" y="32" font-family="Inter, sans-serif" font-size="12" fill="#888888">5 days ago</text>
  </g>

  <g transform="translate(1300, 560)">
    <rect width="560" height="50" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="32" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">YesWeHack - GitLab · $20,000</text>
    <text x="400" y="32" font-family="Inter, sans-serif" font-size="12" fill="#888888">1 week ago</text>
  </g>

  <g transform="translate(1300, 630)">
    <rect width="560" height="50" rx="8" fill="#1A1A1A" stroke="#FFAB00" stroke-width="1" opacity="0.3"/>
    <text x="20" y="32" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Bugcrowd - Shopify · $15,000</text>
    <text x="400" y="32" font-family="Inter, sans-serif" font-size="12" fill="#FFAB00">Pending</text>
  </g>

  <g transform="translate(1300, 700)">
    <rect width="560" height="50" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="32" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">YesWeHack - Mozilla · $30,000</text>
    <text x="400" y="32" font-family="Inter, sans-serif" font-size="12" fill="#888888">2 weeks ago</text>
  </g>
</svg>"""
    return svg


def generate_merlin_demo():
    """MERLIN chat interface demo"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#111115;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="message-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1A1A1A;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>
  </defs>

  <rect width="1920" height="1080" fill="url(#bg-gradient)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1920" height="80" fill="#0B0B0B" stroke="#1A1A1A" stroke-width="1"/>
  <text x="40" y="50" font-family="Inter, sans-serif" font-size="24" font-weight="700" fill="#FFFFFF">MERLIN</text>
  <circle cx="1850" cy="40" r="20" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="1850" cy="40" r="12" fill="#2D7FF9"/>

  <!-- Chat Area -->
  <rect x="40" y="120" width="1200" height="880" rx="12" fill="url(#message-gradient)" stroke="#1A1A1A" stroke-width="1"/>

  <!-- User Message -->
  <g transform="translate(60, 140)">
    <rect width="400" height="80" rx="12" fill="#2D7FF9" opacity="0.2"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Show me the top 3 zero-barrier opportunities</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">2 minutes ago</text>
  </g>

  <!-- MERLIN Response -->
  <g transform="translate(60, 250)">
    <rect width="1000" height="200" rx="12" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1" opacity="0.3"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#2D7FF9">Based on current analysis, here are the top 3 zero-barrier opportunities:</text>
    
    <g transform="translate(20, 50)">
      <circle cx="10" cy="15" r="6" fill="#00C853"/>
      <text x="25" y="20" font-family="Inter, sans-serif" font-size="13" fill="#FFFFFF">HackerOne - Tesla Motors</text>
      <text x="25" y="40" font-family="Inter, sans-serif" font-size="11" fill="#888888">Zero-barrier: 89 · Payout: $50,000 · Ready to submit</text>
    </g>
    
    <g transform="translate(20, 100)">
      <circle cx="10" cy="15" r="6" fill="#00C853"/>
      <text x="25" y="20" font-family="Inter, sans-serif" font-size="13" fill="#FFFFFF">Intigriti - Air France</text>
      <text x="25" y="40" font-family="Inter, sans-serif" font-size="11" fill="#888888">Zero-barrier: 91 · Payout: €25,000 · Evidence ready</text>
    </g>
    
    <g transform="translate(20, 150)">
      <circle cx="10" cy="15" r="6" fill="#00C853"/>
      <text x="25" y="20" font-family="Inter, sans-serif" font-size="13" fill="#FFFFFF">YesWeHack - GitLab</text>
      <text x="25" y="40" font-family="Inter, sans-serif" font-size="11" fill="#888888">Zero-barrier: 78 · Payout: $20,000 · Report generated</text>
    </g>
  </g>

  <!-- User Message 2 -->
  <g transform="translate(60, 480)">
    <rect width="300" height="60" rx="12" fill="#2D7FF9" opacity="0.2"/>
    <text x="20" y="35" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">What's the expected value?</text>
  </g>

  <!-- MERLIN Response 2 -->
  <g transform="translate(60, 570)">
    <rect width="800" height="120" rx="12" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1" opacity="0.3"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#2D7FF9">Expected Value Analysis:</text>
    <text x="20" y="60" font-family="Inter, sans-serif" font-size="13" fill="#FFFFFF">Tesla: $50,000 × 40% acceptance = $20,000 EV</text>
    <text x="20" y="85" font-family="Inter, sans-serif" font-size="13" fill="#FFFFFF">Air France: €25,000 × 55% acceptance = €13,750 EV</text>
    <text x="20" y="110" font-family="Inter, sans-serif" font-size="13" fill="#FFFFFF">GitLab: $20,000 × 35% acceptance = $7,000 EV</text>
  </g>

  <!-- Side Panel -->
  <rect x="1280" y="120" width="600" height="880" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="1300" y="160" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Memory Context</text>

  <g transform="translate(1300, 200)">
    <rect width="560" height="60" rx="8" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1" opacity="0.2"/>
    <text x="20" y="25" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Current Focus</text>
    <text x="20" y="45" font-family="Inter, sans-serif" font-size="12" fill="#888888">HackerOne Tesla analysis</text>
  </g>

  <g transform="translate(1300, 280)">
    <rect width="560" height="60" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="25" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Recent Queries</text>
    <text x="20" y="45" font-family="Inter, sans-serif" font-size="12" fill="#888888">12 today · 87 this week</text>
  </g>

  <g transform="translate(1300, 360)">
    <rect width="560" height="60" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="25" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Learning Progress</text>
    <text x="20" y="45" font-family="Inter, sans-serif" font-size="12" fill="#00C853">23 patterns recognized</text>
  </g>

  <g transform="translate(1300, 440)">
    <rect width="560" height="60" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="25" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Voice Mode</text>
    <text x="20" y="45" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Active · Web Speech API</text>
  </g>
</svg>"""
    return svg


def generate_agents_demo():
    """Agents list demo"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#111115;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="card-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1A1A1A;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>
  </defs>

  <rect width="1920" height="1080" fill="url(#bg-gradient)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1920" height="80" fill="#0B0B0B" stroke="#1A1A1A" stroke-width="1"/>
  <text x="40" y="50" font-family="Inter, sans-serif" font-size="24" font-weight="700" fill="#FFFFFF">Agents</text>
  <circle cx="1850" cy="40" r="20" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="1850" cy="40" r="12" fill="#2D7FF9"/>

  <!-- Agent Cards -->
  <g transform="translate(40, 120)">
    <rect width="840" height="200" rx="12" fill="url(#card-gradient)" stroke="#2D7FF9" stroke-width="1" opacity="0.3"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Security Agent</text>
    <text x="20" y="70" font-family="Inter, sans-serif" font-size="14" fill="#888888">Autonomous vulnerability discovery and validation</text>
    <rect x="20" y="90" width="120" height="30" rx="4" fill="#00C853"/>
    <text x="30" y="110" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">RUNNING</text>
    <text x="20" y="150" font-family="Inter, sans-serif" font-size="12" fill="#888888">Last task: Tesla SQL injection analysis · 5 min ago</text>
    <text x="20" y="175" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Tasks completed: 234 today</text>
  </g>

  <g transform="translate(920, 120)">
    <rect width="840" height="200" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Intelligence Agent</text>
    <text x="20" y="70" font-family="Inter, sans-serif" font-size="14" fill="#888888">Opportunity analysis and pattern recognition</text>
    <rect x="20" y="90" width="120" height="30" rx="4" fill="#00C853"/>
    <text x="30" y="110" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">RUNNING</text>
    <text x="20" y="150" font-family="Inter, sans-serif" font-size="12" fill="#888888">Last task: Platform ranking update · 2 min ago</text>
    <text x="20" y="175" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Tasks completed: 156 today</text>
  </g>

  <g transform="translate(40, 350)">
    <rect width="840" height="200" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Automation Agent</text>
    <text x="20" y="70" font-family="Inter, sans-serif" font-size="14" fill="#888888">Workflow execution and task coordination</text>
    <rect x="20" y="90" width="120" height="30" rx="4" fill="#00C853"/>
    <text x="30" y="110" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">RUNNING</text>
    <text x="20" y="150" font-family="Inter, sans-serif" font-size="12" fill="#888888">Last task: Work bank generation · 10 min ago</text>
    <text x="20" y="175" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Tasks completed: 89 today</text>
  </g>

  <g transform="translate(920, 350)">
    <rect width="840" height="200" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">MERLIN Agent</text>
    <text x="20" y="70" font-family="Inter, sans-serif" font-size="14" fill="#888888">Natural language interface and decision support</text>
    <rect x="20" y="90" width="120" height="30" rx="4" fill="#00C853"/>
    <text x="30" y="110" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">RUNNING</text>
    <text x="20" y="150" font-family="Inter, sans-serif" font-size="12" fill="#888888">Last task: Opportunity query · 1 min ago</text>
    <text x="20" y="175" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Tasks completed: 67 today</text>
  </g>

  <g transform="translate(40, 580)">
    <rect width="840" height="200" rx="12" fill="url(#card-gradient)" stroke="#FFAB00" stroke-width="1" opacity="0.3"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Reporting Agent</text>
    <text x="20" y="70" font-family="Inter, sans-serif" font-size="14" fill="#888888">Report generation and submission coordination</text>
    <rect x="20" y="90" width="120" height="30" rx="4" fill="#FFAB00"/>
    <text x="30" y="110" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">PAUSED</text>
    <text x="20" y="150" font-family="Inter, sans-serif" font-size="12" fill="#888888">Last task: Report formatting · 1 hour ago</text>
    <text x="20" y="175" font-family="Inter, sans-serif" font-size="12" fill="#FFAB00">Tasks completed: 45 today</text>
  </g>

  <g transform="translate(920, 580)">
    <rect width="840" height="200" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Evolution Agent</text>
    <text x="20" y="70" font-family="Inter, sans-serif" font-size="14" fill="#888888">Performance analysis and capability proposals</text>
    <rect x="20" y="90" width="120" height="30" rx="4" fill="#00C853"/>
    <text x="30" y="110" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">RUNNING</text>
    <text x="20" y="150" font-family="Inter, sans-serif" font-size="12" fill="#888888">Last task: Skill gap analysis · 15 min ago</text>
    <text x="20" y="175" font-family="Inter, sans-serif" font-size="12" fill="#00C853">Tasks completed: 23 today</text>
  </g>

  <!-- Stats Panel -->
  <rect x="40" y="810" width="1840" height="230" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="60" y="850" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Agent Performance</text>

  <g transform="translate(60, 880)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Total Tasks Today</text>
    <text x="0" y="30" font-family="Inter, sans-serif" font-size="32" font-weight="700" fill="#2D7FF9">614</text>
  </g>

  <g transform="translate(300, 880)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Success Rate</text>
    <text x="0" y="30" font-family="Inter, sans-serif" font-size="32" font-weight="700" fill="#00C853">94%</text>
  </g>

  <g transform="translate(540, 880)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Avg Task Time</text>
    <text x="0" y="30" font-family="Inter, sans-serif" font-size="32" font-weight="700" fill="#2D7FF9">2.3m</text>
  </g>

  <g transform="translate(780, 880)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">CPU Usage</text>
    <text x="0" y="30" font-family="Inter, sans-serif" font-size="32" font-weight="700" fill="#00C853">23%</text>
  </g>

  <g transform="translate(1020, 880)">
    <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Memory Usage</text>
    <text x="0" y="30" font-family="Inter, sans-serif" font-size="32" font-weight="700" fill="#00C853">1.2GB</text>
  </g>
</svg>"""
    return svg


def generate_reports_demo():
    """Reports demo with report list"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#111115;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="card-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1A1A1A;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>
  </defs>

  <rect width="1920" height="1080" fill="url(#bg-gradient)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1920" height="80" fill="#0B0B0B" stroke="#1A1A1A" stroke-width="1"/>
  <text x="40" y="50" font-family="Inter, sans-serif" font-size="24" font-weight="700" fill="#FFFFFF">Reports</text>
  <circle cx="1850" cy="40" r="20" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="1850" cy="40" r="12" fill="#2D7FF9"/>

  <!-- Stats Cards -->
  <g transform="translate(40, 120)">
    <rect width="400" height="150" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Reports Generated</text>
    <text x="20" y="90" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#2D7FF9">47</text>
    <text x="20" y="120" font-family="Inter, sans-serif" font-size="12" fill="#00C853">This month</text>
  </g>

  <g transform="translate(480, 120)">
    <rect width="400" height="150" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Submitted</text>
    <text x="20" y="90" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#00C853">23</text>
    <text x="20" y="120" font-family="font-family: Inter, sans-serif" font-size="12" fill="#00C853">Awaiting review</text>
  </g>

  <g transform="translate(920, 120)">
    <rect width="400" height="150" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">Accepted</text>
    <text x="20" y="90" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#D4AF37">18</text>
    <text x="20" y="120" font-family="Inter, sans-serif" font-size="12" fill="#00C853">$95,000 total</text>
  </g>

  <g transform="translate(1360, 120)">
    <rect width="400" height="150" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="14" fill="#888888">In Progress</text>
    <text x="20" y="90" font-family="Inter, sans-serif" font-size="48" font-weight="700" fill="#FFAB00">6</text>
    <text x="20" y="120" font-family="Inter, sans-serif" font-size="12" fill="#FFAB00">Evidence gathering</text>
  </g>

  <!-- Report List -->
  <rect x="40" y="300" width="1840" height="700" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
  <text x="60" y="340" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Recent Reports</text>

  <g transform="translate(60, 380)">
    <rect width="1760" height="80" rx="8" fill="#1A1A1A" stroke="#00C853" stroke-width="1" opacity="0.2"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">Tesla Motors - SQL Injection</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">HackerOne · $50,000 bounty · Submitted 2 days ago</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#00C853"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ACCEPTED</text>
  </g>

  <g transform="translate(60, 480)">
    <rect width="1760" height="80" rx="8" fill="#1A1A1A" stroke="#00C853" stroke-width="1" opacity="0.2"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">Air France - IDOR</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">Intigriti · €25,000 bounty · Submitted 5 days ago</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#00C853"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ACCEPTED</text>
  </g>

  <g transform="translate(60, 580)">
    <rect width="1760" height="80" rx="8" fill="#1A1A1A" stroke="#FFAB00" stroke-width="1" opacity="0.3"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">Shopify - XSS</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">Bugcrowd · $15,000 bounty · Submitted 1 week ago</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#FFAB00"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">REVIEW</text>
  </g>

  <g transform="translate(60, 680)">
    <rect width="1760" height="80" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">GitLab - RCE</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">YesWeHack · $20,000 bounty · Submitted 2 weeks ago</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#00C853"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ACCEPTED</text>
  </g>

  <g transform="translate(60, 780)">
    <rect width="1760" height="80" rx="8" fill="#1A1A1A" stroke="#FFAB00" stroke-width="1" opacity="0.3"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">Mozilla - SSRF</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">YesWeHack · $30,000 bounty · Submitted 3 weeks ago</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#FFAB00"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">REVIEW</text>
  </g>

  <g transform="translate(60, 880)">
    <rect width="1760" height="80" rx="8" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="16" font-weight="600" fill="#FFFFFF">MongoDB - Auth Bypass</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">Intigriti · $15,000 bounty · Submitted 1 month ago</text>
    <rect x="1500" y="25" width="100" height="30" rx="4" fill="#00C853"/>
    <text x="1520" y="45" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ACCEPTED</text>
  </g>
</svg>"""
    return svg


def generate_settings_demo():
    """Settings demo with configuration options"""
    svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0B0B0B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#111115;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="card-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1A1A1A;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0B0B0B;stop-opacity:1" />
    </linearGradient>
  </defs>

  <rect width="1920" height="1080" fill="url(#bg-gradient)"/>

  <!-- Header -->
  <rect x="0" y="0" width="1920" height="80" fill="#0B0B0B" stroke="#1A1A1A" stroke-width="1"/>
  <text x="40" y="50" font-family="Inter, sans-serif" font-size="24" font-weight="700" fill="#FFFFFF">Settings</text>
  <circle cx="1850" cy="40" r="20" fill="#2D7FF9" opacity="0.3"/>
  <circle cx="1850" cy="40" r="12" fill="#2D7FF9"/>

  <!-- Settings Sections -->
  <g transform="translate(40, 120)">
    <rect width="840" height="300" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">AI Configuration</text>
    
    <g transform="translate(20, 70)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Primary Provider</text>
      <rect x="0" y="10" width="200" height="30" rx="4" fill="#2D7FF9"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">Ollama (Local)</text>
    </g>
    
    <g transform="translate(20, 130)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Fallback Provider</text>
      <rect x="0" y="10" width="200" height="30" rx="4" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">FCC Proxy</text>
    </g>
    
    <g transform="translate(20, 190)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Model</text>
      <rect x="0" y="10" width="300" height="30" rx="4" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">qwen3-coder:8b</text>
    </g>
    
    <g transform="translate(20, 250)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Budget Limit</text>
      <rect x="0" y="10" width="200" height="30" rx="4" fill="#1A1A1A" stroke="#2D7FF9" stroke-width="1"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">$100/month</text>
    </g>
  </g>

  <g transform="translate(920, 120)">
    <rect width="840" height="300" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Platform Configuration</text>
    
    <g transform="translate(20, 70)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">HackerOne API Key</text>
      <rect x="0" y="10" width="300" height="30" rx="4" fill="#00C853"/>
      <text x="10" y="30" font-family="font-family: Inter, sans-serif" font-size="12" fill="#FFFFFF">✓ Configured</text>
    </g>
    
    <g transform="translate(20, 130)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Bugcrowd API Key</text>
      <rect x="0" y="10" width="300" height="30" rx="4" fill="#00C853"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">✓ Configured</text>
    </g>
    
    <g transform="translate(20, 190)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Intigriti API Key</text>
      <rect x="0" y="10" width="300" height="30" rx="4" fill="#00C853"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">✓ Configured</text>
    </g>
    
    <g transform="translate(20, 250)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">YesWeHack API Key</text>
      <rect x="0" y="10" width="300" height="30" rx="4" fill="#FFAB00"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">Not configured</text>
    </g>
  </g>

  <g transform="translate(40, 450)">
    <rect width="840" height="250" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">Scheduler Settings</text>
    
    <g transform="translate(20, 70)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Discovery Cycle</text>
      <rect x="0" y="10" width="200" height="30" rx="4" fill="#00C853"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">Every 2 hours</text>
    </g>
    
    <g transform="translate(20, 130)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Analysis Cycle</text>
      <rect x="0" y="10" width="200" height="30" rx="4" fill="#00C853"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">Every 4 hours</text>
    </g>
    
    <g transform="translate(20, 190)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Report Generation</text>
      <rect x="0" y="10" width="200" height="30" rx="4" fill="#00C853"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">Every 6 hours</text>
    </g>
  </g>

  <g transform="translate(920, 450)">
    <rect width="840" height="250" rx="12" fill="url(#card-gradient)" stroke="#1A1A1A" stroke-width="1"/>
    <text x="20" y="40" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FFFFFF">System Settings</text>
    
    <g transform="translate(20, 70)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Auto-submit Reports</text>
      <rect x="0" y="10" width="100" height="30" rx="4" fill="#00C853"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ENABLED</text>
    </g>
    
    <g transform="translate(150, 70)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Auto-discovery</text>
      <rect x="0" y="10" width="100" height="30" rx="4" fill="#00C853"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ENABLED</text>
    </g>
    
    <g transform="translate(20, 130)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Auto-optimization</text>
      <rect x="0" y="10" width="100" height="30" rx="4" fill="#FFAB00"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">DISABLED</text>
    </g>
    
    <g transform="translate(150, 130)">
      <text x="0" y="0" font-family="Inter, sans-serif" font-size="14" fill="#888888">Auto-evolution</text>
      <rect x="0" y="10" width="100" height="30" rx="4" fill="#00C853"/>
      <text x="10" y="30" font-family="Inter, sans-serif" font-size="12" fill="#FFFFFF">ENABLED</text>
    </g>
  </g>

  <!-- Danger Zone -->
  <rect x="40" y="730" width="1840" height="300" rx="12" fill="#1A1A1A" stroke="#FF1744" stroke-width="1" opacity="0.3"/>
  <text x="60" y="770" font-family="Inter, sans-serif" font-size="18" font-weight="600" fill="#FF1744">Danger Zone</text>

  <g transform="translate(60, 810)">
    <rect width="800" height="80" rx="8" fill="#FF1744" opacity="0.2"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Reset All Data</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">⚠️ This action cannot be undone</text>
  </g>

  <g transform="translate(900, 810)">
    <rect width="800" height="80" rx="8" fill="#FF1744" opacity="0.2"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Clear All Cache</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">⚠️ Requires restart</text>
  </g>

  <g transform="translate(60, 910)">
    <rect width="800" height="80" rx="8" fill="#FF1744" opacity="0.2"/>
    <text x="20" y="30" font-family="Inter, sans-serif" font-size="14" fill="#FFFFFF">Factory Reset</text>
    <text x="20" y="55" font-family="Inter, sans-serif" font-size="12" fill="#888888">⚠️ Deletes all configuration</text>
  </g>
</svg>"""
    return svg


def main():
    """Generate all demo screenshots"""
    demo_dir = Path("docs/assets/screenshots/desktop")
    demo_dir.mkdir(parents=True, exist_ok=True)

    demos = {
        "mission-control-demo.svg": generate_mission_control_demo(),
        "intelligence-demo.svg": generate_intelligence_demo(),
        "targets-demo.svg": generate_targets_demo(),
        "capital-demo.svg": generate_capital_demo(),
        "merlin-demo.svg": generate_merlin_demo(),
        "agents-demo.svg": generate_agents_demo(),
        "reports-demo.svg": generate_reports_demo(),
        "settings-demo.svg": generate_settings_demo(),
    }

    for filename, content in demos.items():
        filepath = demo_dir / filename
        filepath.write_text(content, encoding="utf-8")
        print(f"Generated: {filepath}")

    # Convert to PNG
    try:
        import cairosvg
        for filename in demos:
            svg_path = demo_dir / filename
            png_path = demo_dir / filename.replace('.svg', '.png')
            try:
                cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=1920, output_height=1080)
                print(f"Generated PNG: {png_path}")
            except Exception as e:
                print(f"Error converting {filename}: {e}")
    except ImportError:
        print("cairosvg not available, SVG only")


if __name__ == "__main__":
    main()
