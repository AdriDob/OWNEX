"""Generate MERLIN Assistant concept.

Represents: Intelligent assistant, voice, memory, explanation educational
No humanoid - Must seem like an intelligent interface
Style: Premium interface
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

def generate_merlin_assistant_concept() -> str:
    """Generate MERLIN Assistant concept (interface, not humanoid)."""
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" width="1200" height="800">
  <defs>
    <linearGradient id="merlinGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{COLORS['primary_main']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{COLORS['primary_light']};stop-opacity:1" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="1200" height="800" fill="url(#merlinGrad)"/>

  <!-- Title -->
  <text x="600" y="50" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="32" font-weight="700" fill="{COLORS['white']}" letter-spacing="2">MERLIN Assistant</text>
  <text x="600" y="80" text-anchor="middle" font-family="Inter, -apple-system, sans-serif"
        font-size="16" fill="{COLORS['accent_cyan']}" letter-spacing="1">Intelligent Interface • Voice • Memory • Explanation</text>

  <!-- Central Interface Core - Not Humanoid -->
  <circle cx="600" cy="400" r="200" fill="none" stroke="{COLORS['accent_cyan']}" stroke-width="2" filter="url(#glow)"/>
  <circle cx="600" cy="400" r="150" fill="url(#merlinGrad)" opacity="0.3"/>
  <circle cx="600" cy="400" r="100" fill="url(#merlinGrad)" opacity="0.5"/>

  <!-- Intelligence Core - Geometric Pattern -->
  <!-- Hexagonal pattern representing intelligence -->
  <polygon points="600,280 704,340 704,460 600,520 496,460 496,340"
           fill="none" stroke="{COLORS['accent_purple']}" stroke-width="2" filter="url(#glow)"/>

  <!-- Inner geometric patterns -->
  <polygon points="600,320 660,355 660,425 600,460 540,425 540,355"
           fill="{COLORS['accent_blue']}" opacity="0.3" filter="url(#glow)"/>

  <!-- Central intelligence point -->
  <circle cx="600" cy="400" r="30" fill="{COLORS['accent_gold']}" filter="url(#glow)"/>

  <!-- Voice Rings (Audio Interface) -->
  <circle cx="600" cy="400" r="120" fill="none" stroke="{COLORS['accent_cyan']}" stroke-width="1" opacity="0.5"/>
  <circle cx="600" cy="400" r="140" fill="none" stroke="{COLORS['accent_cyan']}" stroke-width="1" opacity="0.3"/>
  <circle cx="600" cy="400" r="160" fill="none" stroke="{COLORS['accent_cyan']}" stroke-width="1" opacity="0.2"/>

  <!-- Memory Nodes (Connected to core) -->
  <circle cx="450" cy="400" r="20" fill="{COLORS['accent_purple']}" filter="url(#glow)"/>
  <circle cx="750" cy="400" r="20" fill="{COLORS['accent_purple']}" filter="url(#glow)"/>
  <circle cx="600" cy="250" r="20" fill="{COLORS['accent_blue']}" filter="url(#glow)"/>
  <circle cx="600" cy="550" r="20" fill="{COLORS['accent_blue']}" filter="url(#glow)"/>

  <!-- Connection lines -->
  <line x1="470" y1="400" x2="570" y2="400" stroke="{COLORS['white']}" stroke-width="1" opacity="0.4"/>
  <line x1="730" y1="400" x2="630" y2="400" stroke="{COLORS['white']}" stroke-width="1" opacity="0.4"/>
  <line x1="600" y1="270" x2="600" y2="370" stroke="{COLORS['white']}" stroke-width="1" opacity="0.4"/>
  <line x1="600" y1="530" x2="600" y2="430" stroke="{COLORS['white']}" stroke-width="1" opacity="0.4"/>

  <!-- Chat Interface Panel -->
  <rect x="100" y="620" width="400" height="150" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_cyan']}" stroke-width="1"/>
  <text x="120" y="650" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['accent_cyan']}">Conversation Memory</text>
  <text x="120" y="670" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">User: Explain how the Security Cycle works</text>
  <text x="120" y="690" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_purple']}">MERLIN: The Security Cycle follows Recon → Hypothesis →</text>
  <text x="120" y="710" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_purple']}">Validation → Evidence → Report. Each stage is executed</text>
  <text x="120" y="730" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_purple']}">by autonomous agents with AI-powered analysis.</text>
  <text x="120" y="750" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● 47 conversations stored</text>

  <!-- Explanation Engine Panel -->
  <rect x="700" y="620" width="400" height="150" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_purple']}" stroke-width="1"/>
  <text x="720" y="650" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['accent_purple']}">Explanation Engine</text>
  <text x="720" y="670" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Mode: Teach (explain from scratch)</text>
  <text x="720" y="690" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Personality: Professor (educational)</text>
  <text x="720" y="710" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">Detail Level: High</text>
  <text x="720" y="730" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_gold']}">● 234 explanations provided</text>
  <text x="720" y="750" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Learning: Active</text>

  <!-- Capabilities Panel -->
  <rect x="100" y="100" width="400" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_blue']}" stroke-width="1"/>
  <text x="120" y="130" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['accent_blue']}">Capabilities</text>
  <text x="120" y="150" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Voice Commands (Whisper + Piper)</text>
  <text x="120" y="170" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Context-Aware Recommendations</text>
  <text x="120" y="190" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Educational Explanations</text>
  <text x="120" y="210" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Real-time System Integration</text>

  <!-- Personalization Panel -->
  <rect x="700" y="100" width="400" height="120" rx="8" fill="{COLORS['primary_light']}" stroke="{COLORS['accent_gold']}" stroke-width="1"/>
  <text x="720" y="130" font-family="Inter, sans-serif" font-size="12" font-weight="600" fill="{COLORS['accent_gold']}">Personalization</text>
  <text x="720" y="150" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Tone: Professional</text>
  <text x="720" y="170" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Speed: 1.0x</text>
  <text x="720" y="190" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['white']}" opacity="0.7">● Auto-Explain: Enabled</text>
  <text x="720" y="210" font-family="Inter, sans-serif" font-size="10" fill="{COLORS['accent_emerald']}">● Interrupt Threshold: Risk Only</text>
</svg>'''

    output_path = CONCEPTS_DIR / "merlin_assistant_concept.svg"
    with open(output_path, "w") as f:
        f.write(svg_content)

    return str(output_path)


if __name__ == "__main__":
    print("Generating MERLIN Assistant concept...")

    merlin = generate_merlin_assistant_concept()
    print(f"✓ MERLIN Assistant concept: {merlin}")
    print("  Represents: Intelligent assistant, voice, memory, explanation educational")
    print("  No humanoid - Geometric intelligence interface")
    print("  Style: Premium interface")
    print("  Inspiration: Linear (modern), Apple (elegance), SpaceX (engineering)")

    print(f"\nMERLIN Assistant concept generated in: {CONCEPTS_DIR}")
