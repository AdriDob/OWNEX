"""Generate Mobile Omega concept.

Shows: Android phone, smartwatch, connection with Alpha desktop
Style: Premium mobile concept
Inspiration: Linear (modern), Apple (elegance), SpaceX (engineering)
"""

from pathlib import Path

CONCEPTS_DIR = Path("assets/branding/concepts")
CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)

# Design System Colors
COLORS = {
    "primary_main": "#1A1A1A",
    "primary_light": "#2A2A2A",
    "accent_blue": "#3B82F6",
    "accent_cyan": "#06B6D4",
    "accent_emerald": "#10B981",
    "accent_gold": "#F59E0B",
    "accent_purple": "#8B5CF6",
    "white": "#FFFFFF",
}

def generate_mobile_omega_concept() -> str:
    """Generate Mobile Omega concept (Android + Wear OS)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="1200" height="800">
  <defs>
    <linearGradient id="mobileGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary_main']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['primary_light']};stop-opacity:1" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1200" height="800" fill="url(#mobileGrad)"/>

  <!-- Title -->
  <text x="600" y="50" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="32" font-weight="700" fill="{COLORS['white']}" letter-spacing="2">OWNEX OMEGA</text>
  <text x="600" y="80" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="16" fill="{COLORS['accent_purple']}" letter-spacing="1">Mobile Companion • Android + Wear OS</text>

  <!-- Desktop ALPHA (Background, smaller) -->
  <rect x="400" y="150" width="400" height="280" rx="12" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_blue']}" stroke-width="2" opacity="0.5"/>
  <text x="600" y="180" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="{COLORS['accent_blue']}" opacity="0.5">OWNEX ALPHA (Desktop)</text>
  <text x="600" y="400" text-anchor="middle" font-family="Inter, sans-serif" font-size="12" fill="{COLORS['white']}" opacity="0.3">Connected • Syncing</text>

  <!-- Connection Line (Desktop to Mobile) -->
  <line x1="600" y1="430" x2="600" y2="500" stroke="{COLORS['accent_cyan']}" stroke-width="2" stroke-dasharray="5,5" opacity="0.5"/>
  <circle cx="600" cy="465" r="5" fill="{COLORS['accent_cyan']}" filter="url(#glow)"/>

  <!-- Android Phone (Center, Large) -->
  <rect x="450" y="500" width="300" height="240" rx="20" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_purple']}" stroke-width="3" filter="url(#glow)"/>
  <text x="600" y="530" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="{COLORS['accent_purple']}">Android Companion</text>

  <!-- Phone Screen Content -->
  <rect x="470" y="540" width="260" height="180" rx="8" fill="{COLORS['primary_main']}" opacity="0.8"/>
  <text x="600" y="565" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['accent_cyan']}">Mission Control</text>
  <text x="600" y="585" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● 12 agents active</text>
  <text x="600" y="605" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● 8 workflows running</text>
  <text x="600" y="625" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● $12.4K revenue</text>
  <text x="600" y="645" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_gold']}">● 3 approvals pending</text>
  <text x="600" y="665" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● System: Online</text>
  <text x="600" y="685" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_purple']}">● Sync: Active</text>
  <text x="600" y="705" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.5">Real-time connection</text>

  <!-- Connection Line (Phone to Watch) -->
  <line x1="750" y1="620" x2="850" y2="620" stroke="{COLORS['accent_cyan']}" stroke-width="2" stroke-dasharray="5,5" opacity="0.5"/>
  <circle cx="800" y="620" r="5" fill="{COLORS['accent_cyan']}" filter="url(#glow)"/>

  <!-- Wear OS Watch (Right, Circular) -->
  <circle cx="920" cy="620" r="80" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_gold']}" stroke-width="3" filter="url(#glow)"/>
  <text x="920" y="560" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" font-weight="600" fill="{COLORS['accent_gold']}">Wear OS</text>

  <!-- Watch Screen Content -->
  <circle cx="920" cy="620" r="60" fill="{COLORS['primary_main']}" opacity="0.8"/>
  <text x="920" y="600" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_cyan']}">Health</text>
  <text x="920" y="620" text-anchor="middle" font-family="Inter, sans-serif" font-size="18" font-weight="700" fill="{COLORS['accent_emerald']}">●</text>
  <text x="920" y="640" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">3 pending</text>
  <text x="920" y="660" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_gold']}">1 alert</text>

  <!-- Connection Line (Watch to Desktop - Curved) -->
  <path d="M 920 540 Q 920 400 800 300" stroke="{COLORS['accent_cyan']}" stroke-width="2" stroke-dasharray="5,5" opacity="0.3" fill="none"/>

  <!-- Features Panel -->
  <rect x="50" y="200" width="300" height="350" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_cyan']}" stroke-width="1"/>
  <text x="70" y="230" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['accent_cyan']}">Mobile Features</text>
  <text x="70" y="260" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Dashboard View</text>
  <text x="70" y="280" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Agent Fleet Monitor</text>
  <text x="70" y="300" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Push Notifications</text>
  <text x="70" y="320" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Approval System</text>
  <text x="70" y="340" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● MERLIN Chat</text>
  <text x="70" y="360" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Real-time Sync</text>
  <text x="70" y="380" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Cloud Backup</text>
  <text x="70" y="400" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Location Tracking</text>
  <text x="70" y="420" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Battery Optimization</text>
  <text x="70" y="440" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Secure Auth</text>
  <text x="70" y="460" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Encrypted Sync</text>
  <text x="70" y="480" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Biometric Lock</text>
  <text x="70" y="500" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Remote Control</text>
  <text x="70" y="520" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Offline Mode</text>

  <!-- Sync Panel -->
  <rect x="850" y="200" width="300" height="250" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_purple']}" stroke-width="1"/>
  <text x="870" y="230" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['accent_purple']}">Sync Architecture</text>
  <text x="870" y="260" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Supabase Cloud</text>
  <text x="870" y="280" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Real-time Subscriptions</text>
  <text x="870" y="300" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Event Bus Sync</text>
  <text x="870" y="320" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Data Persistence</text>
  <text x="870" y="340" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Conflict Resolution</text>
  <text x="870" y="360" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Auto-merge</text>
  <text x="870" y="380" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Conflict-free</text>
  <text x="870" y="400" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Instant sync</text>
  <text x="870" y="420" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Bandwidth optimized</text>
  <text x="870" y="440" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Battery aware</text>
</svg>'''

    output_path = CONCEPTS_DIR / "mobile_omega_concept.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Generating Mobile Omega concept...")

    mobile_omega = generate_mobile_omega_concept()
    print(f"✓ Mobile Omega concept: {mobile_omega}")
    print("  Shows: Android phone, smartwatch, connection with Alpha desktop")
    print("  Style: Premium mobile concept")
    print("  Inspiration: Linear (modern), Apple (elegance), SpaceX (engineering)")

    print(f"\nMobile Omega concept generated in: {CONCEPTS_DIR}")
