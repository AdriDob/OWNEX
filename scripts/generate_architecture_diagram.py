"""Generate architecture diagram concept.

Shows: Agents, departments, workflows, memory, evolution engine, providers, voice, mobile companion
Style: Premium diagram
Inspiration: Linear (modern), Apple (elegance), SpaceX (engineering)
"""

from pathlib import Path

ARCHITECTURE_DIR = Path("assets/branding/architecture")
ARCHITECTURE_DIR.mkdir(parents=True, exist_ok=True)

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

def generate_architecture_diagram() -> str:
    """Generate architecture diagram concept."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="1200" height="800">
  <defs>
    <linearGradient id="archGrad" x1="0%" y1="0%" x2="100%" y2="100%">
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
  <rect width="1200" height="800" fill="url(#archGrad)"/>

  <!-- Title -->
  <text x="600" y="40" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="28" font-weight="700" fill="{COLORS['white']}" letter-spacing="2">OWNEX Architecture</text>

  <!-- Top Layer: Mission Control -->
  <rect x="400" y="80" width="400" height="100" rx="12" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_gold']}" stroke-width="2" filter="url(#glow)"/>
  <text x="600" y="115" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="{COLORS['accent_gold']}">MISSION CONTROL</text>
  <text x="600" y="140" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">Dashboard • Analytics • Orchestration</text>
  <text x="600" y="160" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.5">Central Command Hub</text>

  <!-- Middle Layer: Core Systems -->
  <!-- Agents -->
  <rect x="50" y="220" width="200" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_blue']}" stroke-width="1.5"/>
  <text x="150" y="250" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="{COLORS['accent_blue']}">AGENT FLEET</text>
  <text x="150" y="270" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Autonomous Agents</text>
  <text x="150" y="290" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Coders • Researchers</text>
  <text x="150" y="310" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Validators • Executors</text>
  <text x="150" y="330" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.5">24/7 Operation</text>

  <!-- Workflows -->
  <rect x="280" y="220" width="200" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_cyan']}" stroke-width="1.5"/>
  <text x="380" y="250" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="{COLORS['accent_cyan']}">WORKFLOWS</text>
  <text x="380" y="270" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Security Cycle</text>
  <text x="380" y="290" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Forge Cycle</text>
  <text x="380" y="310" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Pulse Cycle</text>
  <text x="380" y="330" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.5">Automation Engine</text>

  <!-- Memory -->
  <rect x="510" y="220" width="200" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_purple']}" stroke-width="1.5"/>
  <text x="610" y="250" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="{COLORS['accent_purple']}">MEMORY LAYER</text>
  <text x="610" y="270" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Knowledge Graph</text>
  <text x="610" y="290" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Context Store</text>
  <text x="610" y="310" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Learning Database</text>
  <text x="610" y="330" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.5">Persistent State</text>

  <!-- Evolution Engine -->
  <rect x="740" y="220" width="200" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_emerald']}" stroke-width="1.5"/>
  <text x="840" y="250" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="{COLORS['accent_emerald']}">EVOLUTION ENGINE</text>
  <text x="840" y="270" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Self-Improvement</text>
  <text x="840" y="290" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Pattern Recognition</text>
  <text x="840" y="310" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Optimization</text>
  <text x="840" y="330" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.5">Continuous Learning</text>

  <!-- Voice -->
  <rect x="970" y="220" width="180" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_gold']}" stroke-width="1.5"/>
  <text x="1060" y="250" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="{COLORS['accent_gold']}">VOICE DEPT</text>
  <text x="1060" y="270" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Conversations</text>
  <text x="1060" y="290" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Explanations</text>
  <text x="1060" y="310" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Commands</text>
  <text x="1060" y="330" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.5">Natural Interface</text>

  <!-- Bottom Layer: Infrastructure -->
  <!-- Providers -->
  <rect x="150" y="380" width="250" height="100" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_blue']}" stroke-width="1.5"/>
  <text x="275" y="410" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="{COLORS['accent_blue']}">AI PROVIDERS</text>
  <text x="275" y="430" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Claude • DeepSeek • Ollama</text>
  <text x="275" y="450" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Devin CLI • OpenCode</text>
  <text x="275" y="470" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.5">Multi-Model Failover</text>

  <!-- Execution Layer -->
  <rect x="430" y="380" width="250" height="100" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_cyan']}" stroke-width="1.5"/>
  <text x="555" y="410" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="{COLORS['accent_cyan']}">EXECUTION LAYER</text>
  <text x="555" y="430" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Compiler • Runtime</text>
  <text x="555" y="450" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">State Machine</text>
  <text x="555" y="470" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.5">Task Execution</text>

  <!-- Database -->
  <rect x="710" y="380" width="250" height="100" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_purple']}" stroke-width="1.5"/>
  <text x="835" y="410" text-anchor="middle" font-family="Inter, sans-serif" font-size="13" font-weight="600" fill="{COLORS['accent_purple']}">DATABASE LAYER</text>
  <text x="835" y="430" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">SQLite • PostgreSQL</text>
  <text x="835" y="450" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Supabase Sync</text>
  <text x="835" y="470" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.5">Cloud Storage</text>

  <!-- Mobile Companion -->
  <rect x="400" y="520" width="400" height="120" rx="12" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_gold']}" stroke-width="2" filter="url(#glow)"/>
  <text x="600" y="550" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" font-weight="600" fill="{COLORS['accent_gold']}">MOBILE COMPANION</text>
  <text x="600" y="570" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">Android • Wear OS</text>
  <text x="600" y="590" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">Real-time Sync • Push Notifications</text>
  <text x="600" y="610" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.7">Control Panel • Remote Access</text>
  <text x="600" y="630" text-anchor="middle" font-family="Inter, sans-serif" font-size="11" fill="{COLORS['white']}" opacity="0.5">Your Intelligence Everywhere</text>

  <!-- Connection Lines -->
  <g stroke="{COLORS['white']}" stroke-width="1" opacity="0.3">
    <!-- Mission Control to Core Systems -->
    <line x1="600" y1="180" x2="150" y2="220"/>
    <line x1="600" y1="180" x2="380" y2="220"/>
    <line x1="600" y1="180" x2="610" y2="220"/>
    <line x1="600" y1="180" x2="840" y2="220"/>
    <line x1="600" y1="180" x2="1060" y2="220"/>

    <!-- Core Systems to Infrastructure -->
    <line x1="150" y1="340" x2="275" y2="380"/>
    <line x1="380" y1="340" x2="555" y2="380"/>
    <line x1="610" y1="340" x2="835" y2="380"/>
    <line x1="840" y1="340" x2="555" y2="380"/>

    <!-- Infrastructure to Mobile -->
    <line x1="275" y1="480" x2="600" y2="520"/>
    <line x1="555" y1="480" x2="600" y2="520"/>
    <line x1="835" y1="480" x2="600" y2="520"/>
  </g>

  <!-- Footer -->
  <text x="600" y="760" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="12" fill="{COLORS['white']}" opacity="0.5" letter-spacing="1">OWNEX OMEGA — Autonomous Personal Operating System</text>
</svg>'''

    output_path = ARCHITECTURE_DIR / "architecture_diagram.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Generating architecture diagram...")

    architecture = generate_architecture_diagram()
    print(f"✓ Architecture diagram: {architecture}")
    print("  Shows: Agents, Workflows, Memory, Evolution Engine, Voice, Providers, Execution, Database, Mobile")
    print("  Style: Premium diagram")
    print("  Inspiration: Linear (modern), Apple (elegance), SpaceX (engineering)")

    print(f"\nArchitecture diagram generated in: {ARCHITECTURE_DIR}")
