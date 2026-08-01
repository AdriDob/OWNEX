"""Generate Product Overview concept.

Shows: Desktop ALPHA + Android OMEGA + Wear OS + MERLIN + Agents + Memory + Evolution Engine.
Inspired by Tesla/Apple/SpaceX/Linear/NVIDIA/PlayStation ecosystem visuals.
"""

from pathlib import Path

CONCEPTS_DIR = Path("assets/branding/concepts")

# Color System
COLORS = {
    "primary": "#00F0FF",  # Cyber Cyan
    "secondary": "#0044FF",  # Deep Blue
    "accent": "#00FF88",  # Emerald
    "background": "#0A0A0A",  # Space Black
    "neutral": "#1A1A1A",  # Dark Gray
    "text": "#FFFFFF",  # Pure White
    "text_secondary": "#E0E0E0"  # Light Gray
}

def generate_product_overview_v2() -> str:
    """Generate Product Overview concept (1600x900)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" width="1600" height="900">
  <defs>
    <linearGradient id="productGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['background']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['neutral']};stop-opacity:1" />
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
  <rect width="1600" height="900" fill="url(#productGrad)"/>

  <!-- Title -->
  <text x="800" y="50" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="36" font-weight="700" fill="{COLORS['text']}" letter-spacing="3">OWNEX Ecosystem</text>
  <text x="800" y="85" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="18" fill="{COLORS['primary']}" letter-spacing="2">Autonomous Personal Operating System</text>

  <!-- Desktop ALPHA (Center, Large) -->
  <rect x="500" y="120" width="600" height="400" rx="12" fill="{COLORS['neutral']}" stroke="{COLORS['primary']}" stroke-width="2" filter="url(#glow)"/>
  <text x="800" y="150" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="600" fill="{COLORS['primary']}">OWNEX ALPHA</text>
  <text x="800" y="175" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="14" fill="{COLORS['text']}" opacity="0.7">Desktop Command Center</text>

  <!-- ALPHA Components -->
  <rect x="520" y="200" width="170" height="80" rx="6" fill="{COLORS['background']}" opacity="0.5"/>
  <text x="540" y="225" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">Agent Fleet</text>
  <text x="540" y="245" font-family="Inter, system-ui, sans-serif" font-size="16" font-weight="700" fill="{COLORS['accent']}">12 Agents</text>

  <rect x="710" y="200" width="170" height="80" rx="6" fill="{COLORS['background']}" opacity="0.5"/>
  <text x="730" y="225" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">Workflows</text>
  <text x="730" y="245" font-family="Inter, system-ui, sans-serif" font-size="16" font-weight="700" fill="{COLORS['secondary']}">8 Active</text>

  <rect x="900" y="200" width="170" height="80" rx="6" fill="{COLORS['background']}" opacity="0.5"/>
  <text x="920" y="225" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">Memory</text>
  <text x="920" y="245" font-family="Inter, system-ui, sans-serif" font-size="16" font-weight="700" fill="{COLORS['primary']}">4.2GB</text>

  <!-- MERLIN Panel -->
  <rect x="520" y="300" width="360" height="100" rx="6" fill="{COLORS['background']}" opacity="0.3"/>
  <text x="540" y="325" font-family="Inter, system-ui, sans-serif" font-size="12" font-weight="600" fill="{COLORS['accent']}">MERLIN Assistant</text>
  <text x="540" y="345" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.7">Voice • Memory • Explanation</text>
  <text x="540" y="365" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.7">Educational • Context-Aware</text>
  <text x="540" y="385" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['accent']}">47 Conversations</text>

  <!-- Evolution Engine Panel -->
  <rect x="900" y="300" width="170" height="100" rx="6" fill="{COLORS['background']}" opacity="0.3"/>
  <text x="920" y="325" font-family="Inter, system-ui, sans-serif" font-size="12" font-weight="600" fill="{COLORS['secondary']}">Evolution</text>
  <text x="920" y="345" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.7">Self-Improvement</text>
  <text x="920" y="365" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['text']}" opacity="0.7">Pattern Recognition</text>
  <text x="920" y="385" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['accent']}">Learning: ON</text>

  <!-- Departments -->
  <text x="520" y="425" font-family="Inter, system-ui, sans-serif" font-size="12" font-weight="600" fill="{COLORS['text']}" opacity="0.7">Departments:</text>
  <text x="520" y="445" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['primary']}">Architecture • Coding • QA • Research • Security • Documentation</text>
  <text x="520" y="465" font-family="Inter, system-ui, sans-serif" font-size="10" fill="{COLORS['accent']}">● All Systems Operational</text>

  <!-- Android OMEGA (Right) -->
  <rect x="1150" y="150" width="300" height="250" rx="8" fill="{COLORS['neutral']}" stroke="{COLORS['secondary']}" stroke-width="2" filter="url(#glow)"/>
  <text x="1300" y="180" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="16" font-weight="600" fill="{COLORS['secondary']}">OWNEX OMEGA</text>
  <text x="1300" y="200" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">Mobile Companion</text>

  <!-- Phone Representation -->
  <rect x="1220" y="220" width="160" height="160" rx="12" fill="{COLORS['background']}" opacity="0.3"/>
  <text x="1300" y="280" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="14" fill="{COLORS['primary']}">Dashboard</text>
  <text x="1300" y="300" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">Notifications</text>
  <text x="1300" y="320" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">Approvals</text>
  <text x="1300" y="340" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['accent']}">Sync: Active</text>

  <!-- Wear OS (Bottom Right) -->
  <circle cx="1300" cy="580" r="60" fill="{COLORS['neutral']}" stroke="{COLORS['accent']}" stroke-width="2" filter="url(#glow)"/>
  <text x="1300" y="540" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" font-weight="600" fill="{COLORS['accent']}">Wear OS</text>
  <circle cx="1300" cy="580" r="45" fill="{COLORS['background']}" opacity="0.3"/>
  <text x="1300" y="575" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['primary']}">Alerts</text>
  <text x="1300" y="595" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['accent']}">3 Pending</text>

  <!-- Connection Lines -->
  <line x1="1100" y1="320" x2="1150" y2="320" stroke="{COLORS['primary']}" stroke-width="2" stroke-dasharray="5,5" opacity="0.5"/>
  <line x1="1100" y1="400" x2="1300" y2="520" stroke="{COLORS['primary']}" stroke-width="2" stroke-dasharray="5,5" opacity="0.3"/>

  <!-- Key Features (Left) -->
  <rect x="50" y="150" width="400" height="300" rx="8" fill="{COLORS['neutral']}" stroke="{COLORS['accent']}" stroke-width="1"/>
  <text x="70" y="180" font-family="Inter, system-ui, sans-serif" font-size="16" font-weight="600" fill="{COLORS['accent']}">Key Features</text>
  <text x="70" y="210" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">● Autonomous Agents</text>
  <text x="70" y="235" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">● Intelligent Memory</text>
  <text x="70" y="260" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">● Self-Improving</text>
  <text x="70" y="285" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">● Multi-Platform</text>
  <text x="70" y="310" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">● Voice-Enabled</text>
  <text x="70" y="335" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">● Real-Time Sync</text>
  <text x="70" y="360" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['text']}" opacity="0.7">● Security First</text>
  <text x="70" y="385" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['accent']}">● 24/7 Autonomous</text>
  <text x="70" y="410" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['accent']}">● Cloud + Local</text>
  <text x="70" y="435" font-family="Inter, system-ui, sans-serif" font-size="12" fill="{COLORS['accent']}">● Enterprise Ready</text>

  <!-- Tagline -->
  <text x="800" y="600" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="28" font-weight="700" fill="{COLORS['text']}" letter-spacing="4">Build. Learn. Automate. Evolve.</text>
  <text x="800" y="640" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
        font-size="16" fill="{COLORS['text']}" opacity="0.7" letter-spacing="2">Your autonomous operating system</text>
</svg>'''

    output_path = CONCEPTS_DIR / "product_overview_v2.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Generating Product Overview concept v2...")
    product_overview = generate_product_overview_v2()
    print(f"✓ Product Overview v2: {product_overview}")
    print("  Shows: Desktop ALPHA + Android OMEGA + Wear OS + MERLIN + Agents + Memory + Evolution")
    print("  Inspired by: Tesla/Apple/SpaceX/Linear/NVIDIA/PlayStation ecosystem visuals")
