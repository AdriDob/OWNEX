#!/usr/bin/env python3
"""
OWNEX Showcase Generator
Creates desktop and mobile showcase visuals in premium minimal style
"""

import os
from pathlib import Path

# Brand colors from new identity
COLORS = {
    'cosmos': '#08090A',
    'surface': '#111113',
    'surface_alt': '#1F2023',
    'text_primary': '#F6F8FB',
    'text_secondary': '#8B8D98',
    'accent': '#5E6AD2',
    'accent_hover': '#7B85E0',
    'success': '#00E39A',
    'white': '#FFFFFF',
    'black': '#000000',
}

def create_desktop_showcase():
    """
    Creates desktop showcase showing Mission Control interface
    Minimal, dashboard-style mockup
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="1200" height="800" viewBox="0 0 1200 800" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="1200" height="800" fill="{COLORS['cosmos']}"/>

  <!-- Window frame -->
  <rect x="50" y="50" width="1100" height="700" rx="8" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>

  <!-- Window title bar -->
  <rect x="50" y="50" width="1100" height="48" rx="8" fill="{COLORS['surface_alt']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <rect x="50" y="90" width="1100" height="8" fill="{COLORS['surface_alt']}"/>

  <!-- Window controls -->
  <circle cx="80" cy="74" r="6" fill="#FF5F57"/>
  <circle cx="105" cy="74" r="6" fill="#FEBC2E"/>
  <circle cx="130" cy="74" r="6" fill="#28C840"/>

  <!-- Title -->
  <text x="600" y="80" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="14" fill="{COLORS['text_secondary']}">OWNEX ALPHA — Mission Control</text>

  <!-- Sidebar -->
  <rect x="50" y="98" width="200" height="652" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>

  <!-- Navigation items -->
  <rect x="50" y="98" width="200" height="40" fill="{COLORS['surface_alt']}" opacity="0.5"/>
  <text x="70" y="125" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="13" fill="{COLORS['text_primary']}">Dashboard</text>

  <text x="70" y="175" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="13" fill="{COLORS['text_secondary']}">Agents</text>
  <text x="70" y="215" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="13" fill="{COLORS['text_secondary']}">Workflows</text>
  <text x="70" y="255" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="13" fill="{COLORS['text_secondary']}">Opportunities</text>
  <text x="70" y="295" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="13" fill="{COLORS['text_secondary']}">Reports</text>
  <text x="70" y="335" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="13" fill="{COLORS['text_secondary']}">Memory</text>

  <!-- Main content area -->
  <rect x="250" y="98" width="900" height="652" fill="{COLORS['cosmos']}"/>

  <!-- Dashboard metrics -->
  <rect x="270" y="120" width="200" height="100" rx="4" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <text x="290" y="145" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">System Health</text>
  <text x="290" y="175" font-family="'Inter Display', system-ui, sans-serif" font-weight="700" font-size="24" fill="{COLORS['success']}">98%</text>

  <rect x="490" y="120" width="200" height="100" rx="4" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <text x="510" y="145" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">Active Agents</text>
  <text x="510" y="175" font-family="'Inter Display', system-ui, sans-serif" font-weight="700" font-size="24" fill="{COLORS['accent']}">12</text>

  <rect x="710" y="120" width="200" height="100" rx="4" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <text x="730" y="145" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">Revenue (MTD)</text>
  <text x="730" y="175" font-family="'Inter Display', system-ui, sans-serif" font-weight="700" font-size="24" fill="{COLORS['text_primary']}">$4,250</text>

  <rect x="930" y="120" width="200" height="100" rx="4" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <text x="950" y="145" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">Opportunities</text>
  <text x="950" y="175" font-family="'Inter Display', system-ui, sans-serif" font-weight="700" font-size="24" fill="{COLORS['text_primary']}">47</text>

  <!-- Agent fleet section -->
  <text x="270" y="260" font-family="'Inter Display', system-ui, sans-serif" font-weight="600" font-size="18" fill="{COLORS['text_primary']}">Agent Fleet</text>

  <rect x="270" y="280" width="860" height="60" rx="4" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <circle cx="300" cy="310" r="8" fill="{COLORS['success']}"/>
  <text x="320" y="315" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="14" fill="{COLORS['text_primary']}">Security Agent</text>
  <text x="1050" y="315" text-anchor="end" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">Active</text>

  <rect x="270" y="350" width="860" height="60" rx="4" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <circle cx="300" cy="380" r="8" fill="{COLORS['accent']}"/>
  <text x="320" y="385" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="14" fill="{COLORS['text_primary']}">Engineering Agent</text>
  <text x="1050" y="385" text-anchor="end" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">Processing</text>

  <rect x="270" y="420" width="860" height="60" rx="4" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <circle cx="300" cy="450" r="8" fill="{COLORS['success']}"/>
  <text x="320" y="455" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="14" fill="{COLORS['text_primary']}">Revenue Agent</text>
  <text x="1050" y="455" text-anchor="end" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">Active</text>

  <!-- Recent activity -->
  <text x="270" y="520" font-family="'Inter Display', system-ui, sans-serif" font-weight="600" font-size="18" fill="{COLORS['text_primary']}">Recent Activity</text>

  <rect x="270" y="540" width="860" height="200" rx="4" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>

  <text x="290" y="570" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">14:32</text>
  <text x="350" y="570" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="13" fill="{COLORS['text_primary']}">Security Agent completed vulnerability scan on target-42</text>

  <text x="290" y="600" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">14:28</text>
  <text x="350" y="600" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="13" fill="{COLORS['text_primary']}">Evolution Engine scheduled self-update to v7.1.0</text>

  <text x="290" y="630" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">14:15</text>
  <text x="350" y="630" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="13" fill="{COLORS['text_primary']}">Revenue Agent identified new opportunity ($1,200 EV)</text>

  <text x="290" y="660" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">13:45</text>
  <text x="350" y="660" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="13" fill="{COLORS['text_primary']}">MERLIN completed knowledge sync with unified memory</text>

  <text x="290" y="690" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">13:30</text>
  <text x="350" y="690" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="13" fill="{COLORS['text_primary']}">Orchestrator approved workflow execution</text>
</svg>"""
    return svg

def create_mobile_showcase():
    """
    Creates mobile showcase showing OMEGA interface
    Minimal, mobile app mockup
    """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="400" height="800" viewBox="0 0 400 800" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="400" height="800" fill="{COLORS['cosmos']}"/>

  <!-- Phone frame -->
  <rect x="25" y="25" width="350" height="750" rx="40" fill="{COLORS['surface']}" stroke="{COLORS['surface_alt']}" stroke-width="2"/>

  <!-- Phone notch -->
  <rect x="150" y="35" width="100" height="25" rx="12" fill="{COLORS['cosmos']}"/>

  <!-- Status bar -->
  <text x="60" y="55" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="12" fill="{COLORS['text_primary']}">9:41</text>
  <circle cx="330" cy="50" r="4" fill="{COLORS['success']}"/>
  <circle cx="345" cy="50" r="4" fill="{COLORS['text_secondary']}"/>

  <!-- App header -->
  <text x="200" y="100" text-anchor="middle" font-family="'Inter Display', system-ui, sans-serif" font-weight="700" font-size="24" fill="{COLORS['text_primary']}">OWNEX</text>
  <text x="200" y="125" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">OMEGA</text>

  <!-- Quick status cards -->
  <rect x="50" y="150" width="300" height="80" rx="8" fill="{COLORS['surface_alt']}" stroke="{COLORS['accent']}" stroke-width="1"/>
  <text x="70" y="175" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">System Status</text>
  <text x="70" y="200" font-family="'Inter Display', system-ui, sans-serif" font-weight="700" font-size="20" fill="{COLORS['success']}">Online</text>
  <text x="300" y="200" text-anchor="end" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">12 agents</text>

  <rect x="50" y="240" width="300" height="80" rx="8" fill="{COLORS['surface_alt']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <text x="70" y="265" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">Pending Approvals</text>
  <text x="70" y="290" font-family="'Inter Display', system-ui, sans-serif" font-weight="700" font-size="20" fill="{COLORS['accent']}">3</text>
  <text x="300" y="290" text-anchor="end" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">Action needed</text>

  <!-- MERLIN chat preview -->
  <text x="50" y="360" font-family="'Inter Display', system-ui, sans-serif" font-weight="600" font-size="16" fill="{COLORS['text_primary']}">MERLIN</text>

  <rect x="50" y="380" width="300" height="60" rx="8" fill="{COLORS['surface_alt']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>
  <text x="70" y="405" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['text_secondary']}">System</text>
  <text x="70" y="425" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="13" fill="{COLORS['text_primary']}">Daily summary ready for review</text>

  <rect x="50" y="450" width="300" height="60" rx="8" fill="{COLORS['success']}" fill-opacity="0.1" stroke="{COLORS['success']}" stroke-width="1"/>
  <text x="70" y="475" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="12" fill="{COLORS['success']}">MERLIN</text>
  <text x="70" y="495" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="13" fill="{COLORS['text_primary']}">2 new insights from today's work</text>

  <!-- Bottom navigation -->
  <rect x="25" y="700" width="350" height="75" rx="0" fill="{COLORS['surface_alt']}" stroke="{COLORS['surface_alt']}" stroke-width="1"/>

  <circle cx="100" cy="737" r="6" fill="{COLORS['accent']}"/>
  <text x="100" y="760" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="500" font-size="10" fill="{COLORS['text_primary']}">Home</text>

  <circle cx="200" cy="737" r="6" fill="{COLORS['text_secondary']}"/>
  <text x="200" y="760" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="10" fill="{COLORS['text_secondary']}">Agents</text>

  <circle cx="300" cy="737" r="6" fill="{COLORS['text_secondary']}"/>
  <text x="300" y="760" text-anchor="middle" font-family="'Inter', system-ui, sans-serif" font-weight="400" font-size="10" fill="{COLORS['text_secondary']}">Settings</text>
</svg>"""
    return svg

def save_svg(svg_content, filepath):
    """Save SVG content to file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(svg_content)
    print(f"Created: {filepath}")

def main():
    """Generate all showcase assets"""
    concepts_dir = Path("assets/concepts")
    concepts_dir.mkdir(parents=True, exist_ok=True)

    # Generate showcase visuals
    print("Generating showcase visuals...")
    save_svg(create_desktop_showcase(), concepts_dir / "desktop-showcase.svg")
    save_svg(create_mobile_showcase(), concepts_dir / "mobile-showcase.svg")

    print("\n✓ All showcase visuals generated successfully")
    print(f"Output directory: {concepts_dir.absolute()}")

if __name__ == "__main__":
    main()
