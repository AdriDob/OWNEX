"""Generate custom OWNEX ALPHA and OMEGA logos.

Generates professional logos specifically for:
- OWNEX ALPHA (Desktop edition)
- OWNEX OMEGA (Mobile edition)
"""

from pathlib import Path
import math

class OwnexLogoGenerator:
    """Generate custom OWNEX ALPHA and OMEGA logos"""

    def __init__(self, output_dir: str = "assets/branding/logos-custom"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Brand colors
        self.colors = {
            "ownex_blue": "#3B82F6",
            "ownex_white": "#F0F0F0",
            "ownex_gold": "#F59E0B",
            "alpha_dark": "#0F172A",
            "omega_dark": "#1E293B",
            "accent_cyan": "#06B6D4",
            "accent_purple": "#8B5CF6",
        }

    def generate_alpha_logo(self) -> str:
        """Generate OWNEX ALPHA logo for desktop edition.

        ALPHA = Desktop edition (professional, robust, enterprise-grade)
        Design: Strong, geometric, authoritative
        """
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <defs>
    <linearGradient id="alphaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['accent_cyan']};stop-opacity:1" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Outer hexagon - strong geometric shape -->
  <polygon points="200,30 350,115 350,285 200,370 50,285 50,115"
           fill="none" stroke="url(#alphaGrad)" stroke-width="4" filter="url(#glow)"/>

  <!-- Inner hexagon -->
  <polygon points="200,60 320,160 320,240 200,340 80,240 80,160"
           fill="url(#alphaGrad)" opacity="0.2"/>

  <!-- Core triangle - ALPHA symbol -->
  <polygon points="200,100 260,220 200,280 140,220"
           fill="{self.colors['ownex_white']}" filter="url(#glow)"/>

  <!-- A letter inside -->
  <text x="200" y="200" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="60" font-weight="bold" fill="{self.colors['alpha_dark']}">A</text>

  <!-- Ownex text -->
  <text x="200" y="300" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="32" font-weight="bold" fill="{self.colors['ownex_white']}">OWNEX</text>

  <!-- Alpha text -->
  <text x="200" y="335" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="20" font-weight="bold" fill="{self.colors['accent_cyan']}">ALPHA</text>
</svg>'''

        output_path = self.output_dir / "ownex_alpha_logo.svg"
        with open(output_path, "w") as f:
            f.write(svg_content)

        return str(output_path)

    def generate_omega_logo(self) -> str:
        """Generate OWNEX OMEGA logo for mobile edition.

        OMEGA = Mobile edition (smartphone, wearable, companion)
        Design: Modern, sleek, mobile-first
        """
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <defs>
    <linearGradient id="omegaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['accent_purple']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Circle - mobile/rounded shape -->
  <circle cx="200" cy="200" r="180"
          fill="none" stroke="url(#omegaGrad)" stroke-width="4" filter="url(#glow)"/>

  <!-- Inner circle -->
  <circle cx="200" cy="200" r="140"
          fill="url(#omegaGrad)" opacity="0.2"/>

  <!-- Omega symbol Ω -->
  <text x="200" y="180" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="100" font-weight="bold" fill="{self.colors['ownex_white']}" filter="url(#glow)">Ω</text>

  <!-- Ownex text -->
  <text x="200" y="300" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="32" font-weight="bold" fill="{self.colors['ownex_white']}">OWNEX</text>

  <!-- Omega text -->
  <text x="200" y="335" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="20" font-weight="bold" fill="{self.colors['accent_purple']}">OMEGA</text>
</svg>'''

        output_path = self.output_dir / "ownex_omega_logo.svg"
        with open(output_path, "w") as f:
            f.write(svg_content)

        return str(output_path)

    def generate_ai_hero_banner(self) -> str:
        """Generate AI-themed hero banner (not planet earth).

        Focus: AI, technology, code, data, neural networks
        """
        svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" height="400">
  <defs>
    <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['alpha_dark']};stop-opacity:1" />
      <stop offset="50%" style="stop-color:{self.colors['omega_dark']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="1200" height="400" fill="url(#heroGrad)"/>

  <!-- Neural network nodes (AI theme) -->
  <circle cx="200" cy="200" r="30" fill="{self.colors['accent_cyan']}" opacity="0.6"/>
  <circle cx="400" cy="150" r="25" fill="{self.colors['accent_purple']}" opacity="0.6"/>
  <circle cx="400" cy="250" r="25" fill="{self.colors['accent_purple']}" opacity="0.6"/>
  <circle cx="600" cy="200" r="35" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="800" cy="120" r="20" fill="{self.colors['accent_cyan']}" opacity="0.6"/>
  <circle cx="800" cy="280" r="20" fill="{self.colors['accent_cyan']}" opacity="0.6"/>
  <circle cx="1000" cy="200" r="30" fill="{self.colors['accent_purple']}" opacity="0.6"/>

  <!-- Neural network connections -->
  <line x1="200" y1="200" x2="400" y2="150" stroke="{self.colors['ownex_white']}" stroke-width="2" opacity="0.3"/>
  <line x1="200" y1="200" x2="400" y2="250" stroke="{self.colors['ownex_white']}" stroke-width="2" opacity="0.3"/>
  <line x1="400" y1="150" x2="600" y2="200" stroke="{self.colors['ownex_white']}" stroke-width="2" opacity="0.3"/>
  <line x1="400" y1="250" x2="600" y2="200" stroke="{self.colors['ownex_white']}" stroke-width="2" opacity="0.3"/>
  <line x1="600" y1="200" x2="800" y2="120" stroke="{self.colors['ownex_white']}" stroke-width="2" opacity="0.3"/>
  <line x1="600" y1="200" x2="800" y2="280" stroke="{self.colors['ownex_white']}" stroke-width="2" opacity="0.3"/>
  <line x1="800" y1="120" x2="1000" y2="200" stroke="{self.colors['ownex_white']}" stroke-width="2" opacity="0.3"/>
  <line x1="800" y1="280" x2="1000" y2="200" stroke="{self.colors['ownex_white']}" stroke-width="2" opacity="0.3"/>

  <!-- Data streams (code/data theme) -->
  <rect x="50" y="320" width="100" height="10" fill="{self.colors['accent_cyan']}" opacity="0.4"/>
  <rect x="50" y="340" width="80" height="10" fill="{self.colors['accent_cyan']}" opacity="0.3"/>
  <rect x="50" y="360" width="120" height="10" fill="{self.colors['accent_cyan']}" opacity="0.5"/>

  <rect x="1050" y="320" width="100" height="10" fill="{self.colors['accent_purple']}" opacity="0.4"/>
  <rect x="1070" y="340" width="80" height="10" fill="{self.colors['accent_purple']}" opacity="0.3"/>
  <rect x="1030" y="360" width="120" height="10" fill="{self.colors['accent_purple']}" opacity="0.5"/>

  <!-- Title -->
  <text x="600" y="100" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="48" font-weight="bold" fill="{self.colors['ownex_white']}">OWNEX OMEGA</text>

  <!-- Subtitle -->
  <text x="600" y="140" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="24" fill="{self.colors['ownex_gold']}">Autonomous AI Workforce</text>
</svg>'''

        output_path = self.output_dir / "ai_hero_banner.svg"
        with open(output_path, "w") as f:
            f.write(svg_content)

        return str(output_path)


if __name__ == "__main__":
    generator = OwnexLogoGenerator()

    print("Generating custom OWNEX logos...")
    alpha_logo = generator.generate_alpha_logo()
    print(f"✓ Alpha logo: {alpha_logo}")

    omega_logo = generator.generate_omega_logo()
    print(f"✓ Omega logo: {omega_logo}")

    hero_banner = generator.generate_ai_hero_banner()
    print(f"✓ AI hero banner: {hero_banner}")

    print(f"\nAll custom logos generated in: {generator.output_dir}")
