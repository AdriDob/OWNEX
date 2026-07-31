#!/usr/bin/env python3
"""
OWNEX Production Asset Generator
Create optimized production versions of winning concepts
"""

import json
from pathlib import Path
from typing import Dict, Any

class ProductionGenerator:
    """Generate production-ready brand assets"""
    
    def __init__(self, concepts_dir: str = ".ai/brand/concepts", output_dir: str = ".ai/brand/approved"):
        self.concepts_dir = Path(concepts_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Brand colors
        self.colors = {
            "ownex_blue": "#3B82F6",
            "ownex_white": "#F0F0F0",
            "ownex_gold": "#F59E0B",
            "bg_deep": "#050505",
            "bg_base": "#080808",
            "bg_surface": "#0F1117",
            "bg_elevated": "#14161E"
        }
    
    def load_evaluation_results(self) -> Dict[Any, Any]:
        """Load evaluation results"""
        eval_path = self.concepts_dir / "evaluation_results.json"
        
        with open(eval_path) as f:
            return json.load(f)
    
    def create_production_logo(self, concept_id: int) -> str:
        """Create production-ready logo based on winning concept"""
        
        # Concept 6: Value Integration (winner)
        logo_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="valueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
      <stop offset="70%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:0.9" />
      <stop offset="100%" style="stop-color:{self.colors['ownex_gold']};stop-opacity:1" />
    </linearGradient>
    <filter id="subtleGlow">
      <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  
  <!-- Main circle with gradient -->
  <circle cx="100" cy="100" r="70" fill="none" stroke="url(#valueGrad)" stroke-width="4" filter="url(#subtleGlow)"/>
  
  <!-- Inner circle -->
  <circle cx="100" cy="100" r="45" fill="{self.colors['ownex_blue']}" opacity="0.85"/>
  
  <!-- Cross elements (value integration) -->
  <path d="M100 55 L 100 145" stroke="{self.colors['ownex_gold']}" stroke-width="3" opacity="0.85"/>
  <path d="M55 100 L 145 100" stroke="{self.colors['ownex_gold']}" stroke-width="3" opacity="0.85"/>
  
  <!-- Center core -->
  <circle cx="100" cy="100" r="15" fill="{self.colors['ownex_gold']}" opacity="0.95"/>
  
  <!-- Outer accent dots -->
  <circle cx="100" cy="30" r="4" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="100" cy="170" r="4" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="30" cy="100" r="4" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="170" cy="100" r="4" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
</svg>'''
        
        return self._save_asset(logo_svg, "logos/ownex-logo-production.svg")
    
    def create_production_hero(self, concept_id: int) -> str:
        """Create production-ready hero banner"""
        
        # Concept 1: Mission Control (winner)
        hero_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['bg_deep']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['bg_base']};stop-opacity:1" />
    </linearGradient>
    <pattern id="heroGrid" width="60" height="60" patternUnits="userSpaceOnUse">
      <path d="M 60 0 L 0 0 0 60" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="0.5" opacity="0.08"/>
    </pattern>
    <filter id="glow">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  
  <!-- Background -->
  <rect width="1920" height="1080" fill="url(#heroGrad)"/>
  <rect width="1920" height="1080" fill="url(#heroGrid)"/>
  
  <!-- Central hero element -->
  <circle cx="960" cy="540" r="250" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.3"/>
  <circle cx="960" cy="540" r="180" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="1.5" opacity="0.2"/>
  <circle cx="960" cy="540" r="120" fill="{self.colors['ownex_blue']}" opacity="0.08"/>
  
  <!-- Data flow lines -->
  <line x1="160" y1="540" x2="710" y2="540" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.25"/>
  <line x1="1210" y1="540" x2="1760" y2="540" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.25"/>
  <line x1="960" y1="160" x2="960" y2="420" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.25"/>
  <line x1="960" y1="660" x2="960" y2="920" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.25"/>
  
  <!-- Central core -->
  <circle cx="960" cy="540" r="80" fill="{self.colors['ownex_blue']}" opacity="0.15"/>
  <circle cx="960" cy="540" r="50" fill="{self.colors['ownex_blue']}" opacity="0.25"/>
  <circle cx="960" cy="540" r="25" fill="{self.colors['ownex_blue']}" opacity="0.4" filter="url(#glow)"/>
  
  <!-- Accent points -->
  <circle cx="710" cy="540" r="6" fill="{self.colors['ownex_gold']}" opacity="0.8" filter="url(#glow)"/>
  <circle cx="1210" cy="540" r="6" fill="{self.colors['ownex_gold']}" opacity="0.8" filter="url(#glow)"/>
  <circle cx="960" cy="420" r="6" fill="{self.colors['ownex_gold']}" opacity="0.8" filter="url(#glow)"/>
  <circle cx="960" cy="660" r="6" fill="{self.colors['ownex_gold']}" opacity="0.8" filter="url(#glow)"/>
  
  <!-- Text -->
  <text x="960" y="980" text-anchor="middle" font-family="Arial, sans-serif" font-size="28" font-weight="600" fill="{self.colors['ownex_white']}" opacity="0.9" letter-spacing="4">OWNEX OMEGA</text>
  <text x="960" y="1015" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="400" fill="{self.colors['ownex_blue']}" opacity="0.8" letter-spacing="2">AUTONOMOUS WORK OPERATING SYSTEM</text>
</svg>'''
        
        return self._save_asset(hero_svg, "heroes/ownex-hero-production.svg")
    
    def create_production_icons(self) -> Dict[str, Any]:
        """Create production-ready work cycle icons"""
        
        icons = {
            "security": f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <path d="M32 8 L 56 16 L 56 32 Q 56 48 32 56 Q 8 48 8 32 L 8 16 Z" 
        fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2.5" opacity="0.9"/>
  <circle cx="32" cy="32" r="10" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <circle cx="32" cy="32" r="4" fill="{self.colors['ownex_white']}" opacity="0.9"/>
</svg>''',
            
            "forge": f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect x="16" y="28" width="32" height="8" fill="{self.colors['ownex_blue']}" opacity="0.8" rx="2"/>
  <rect x="28" y="20" width="8" height="24" fill="{self.colors['ownex_blue']}" opacity="0.9" rx="1"/>
  <circle cx="32" cy="44" r="6" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <circle cx="32" cy="44" r="2" fill="{self.colors['ownex_white']}" opacity="0.9"/>
</svg>''',
            
            "pulse": f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <polyline points="8,32 20,32 28,20 36,44 44,32 56,32" 
            fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2.5" opacity="0.9"/>
  <circle cx="32" cy="32" r="5" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <circle cx="32" cy="32" r="2" fill="{self.colors['ownex_white']}" opacity="0.9"/>
</svg>''',
            
            "vault": f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect x="12" y="16" width="40" height="32" fill="none" stroke="{self.colors['ownex_gold']}" stroke-width="2.5" opacity="0.9" rx="4"/>
  <circle cx="32" cy="32" r="8" fill="none" stroke="{self.colors['ownex_gold']}" stroke-width="2" opacity="0.8"/>
  <circle cx="32" cy="32" r="3" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>''',
            
            "atlas": f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <circle cx="32" cy="32" r="20" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2.5" opacity="0.9"/>
  <ellipse cx="32" cy="32" rx="20" ry="8" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="1.5" opacity="0.6"/>
  <ellipse cx="32" cy="32" rx="8" ry="20" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="1.5" opacity="0.6"/>
  <circle cx="32" cy="32" r="4" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <circle cx="32" cy="32" r="1.5" fill="{self.colors['ownex_white']}" opacity="0.9"/>
</svg>'''
        }
        
        generated = {}
        for icon_type, svg_content in icons.items():
            filepath = self._save_asset(svg_content, f"icons/{icon_type}-production.svg")
            generated[icon_type] = filepath
        
        return generated
    
    def create_logo_variations(self) -> Dict[str, Any]:
        """Create logo variations for different sizes and contexts"""
        
        base_logo = self.create_production_logo(6)
        
        variations = {}
        
        # Monochrome version
        mono_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <circle cx="100" cy="100" r="70" fill="none" stroke="{self.colors['ownex_white']}" stroke-width="4"/>
  <circle cx="100" cy="100" r="45" fill="{self.colors['ownex_white']}" opacity="0.85"/>
  <path d="M100 55 L 100 145" stroke="{self.colors['ownex_white']}" stroke-width="3" opacity="0.85"/>
  <path d="M55 100 L 145 100" stroke="{self.colors['ownex_white']}" stroke-width="3" opacity="0.85"/>
  <circle cx="100" cy="100" r="15" fill="{self.colors['ownex_white']}" opacity="0.95"/>
</svg>'''
        variations["monochrome"] = self._save_asset(mono_svg, "logos/ownex-logo-monochrome.svg")
        
        # Small version (32px optimized)
        small_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
  <circle cx="16" cy="16" r="12" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2"/>
  <circle cx="16" cy="16" r="7" fill="{self.colors['ownex_blue']}" opacity="0.85"/>
  <path d="M16 9 L 16 23" stroke="{self.colors['ownex_gold']}" stroke-width="1.5" opacity="0.85"/>
  <path d="M9 16 L 23 16" stroke="{self.colors['ownex_gold']}" stroke-width="1.5" opacity="0.85"/>
  <circle cx="16" cy="16" r="2.5" fill="{self.colors['ownex_gold']}" opacity="0.95"/>
</svg>'''
        variations["small"] = self._save_asset(small_svg, "logos/ownex-logo-32px.svg")
        
        # Icon-only version (isotype)
        isotype_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <circle cx="32" cy="32" r="24" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="3"/>
  <circle cx="32" cy="32" r="14" fill="{self.colors['ownex_blue']}" opacity="0.85"/>
  <path d="M32 18 L 32 46" stroke="{self.colors['ownex_gold']}" stroke-width="2" opacity="0.85"/>
  <path d="M18 32 L 46 32" stroke="{self.colors['ownex_gold']}" stroke-width="2" opacity="0.85"/>
  <circle cx="32" cy="32" r="5" fill="{self.colors['ownex_gold']}" opacity="0.95"/>
</svg>'''
        variations["isotype"] = self._save_asset(isotype_svg, "logos/ownex-isotype.svg")
        
        return variations
    
    def _save_asset(self, svg_content: str, filename: str) -> str:
        """Save production asset to file"""
        filepath = self.output_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(svg_content)
        
        return str(filepath)
    
    def generate_all_production_assets(self):
        """Generate all production assets from winning concepts"""
        
        print("Generating OWNEX OMEGA production assets...")
        
        # Load evaluation results
        results = self.load_evaluation_results()
        
        # Generate production logo
        best_logo_id = results["best_logo"]["concept_id"]
        print(f"Creating production logo (Concept {best_logo_id})...")
        logo_path = self.create_production_logo(best_logo_id)
        print(f"  ✓ Production logo: {logo_path}")
        
        # Generate logo variations
        print("Creating logo variations...")
        variations = self.create_logo_variations()
        for variant, path in variations.items():
            print(f"  ✓ {variant}: {path}")
        
        # Generate production hero
        best_hero_id = results["best_hero"]["concept_id"]
        print(f"Creating production hero (Concept {best_hero_id})...")
        hero_path = self.create_production_hero(best_hero_id)
        print(f"  ✓ Production hero: {hero_path}")
        
        # Generate production icons
        print("Creating production work cycle icons...")
        icons = self.create_production_icons()
        for icon_type, path in icons.items():
            print(f"  ✓ {icon_type}: {path}")
        
        print(f"\n✓ All production assets generated in {self.output_dir}")
        
        return {
            "logo": logo_path,
            "variations": variations,
            "hero": hero_path,
            "icons": icons
        }
    
    def create_social_preview(self) -> str:
        """Create social preview image for GitHub/LinkedIn"""
        
        social_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <defs>
    <linearGradient id="socialGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['bg_deep']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['bg_base']};stop-opacity:1" />
    </linearGradient>
    <pattern id="socialGrid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="0.5" opacity="0.1"/>
    </pattern>
  </defs>
  
  <!-- Background -->
  <rect width="1200" height="630" fill="url(#socialGrad)"/>
  <rect width="1200" height="630" fill="url(#socialGrid)"/>
  
  <!-- Logo -->
  <circle cx="600" cy="280" r="100" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="4" opacity="0.8"/>
  <circle cx="600" cy="280" r="60" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <path d="M600 220 L 600 340" stroke="{self.colors['ownex_gold']}" stroke-width="3" opacity="0.8"/>
  <path d="M540 280 L 660 280" stroke="{self.colors['ownex_gold']}" stroke-width="3" opacity="0.8"/>
  <circle cx="600" cy="280" r="20" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
  
  <!-- Title -->
  <text x="600" y="450" text-anchor="middle" font-family="Arial, sans-serif" font-size="48" font-weight="700" fill="{self.colors['ownex_white']}" letter-spacing="4">OWNEX OMEGA</text>
  
  <!-- Tagline -->
  <text x="600" y="500" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="400" fill="{self.colors['ownex_blue']}" letter-spacing="2">AUTONOMOUS WORK OPERATING SYSTEM</text>
  
  <!-- Accent line -->
  <line x1="400" y1="530" x2="800" y2="530" stroke="{self.colors['ownex_gold']}" stroke-width="2" opacity="0.6"/>
</svg>'''
        
        return self._save_asset(social_svg, "social/ownex-social-preview.svg")
    
    def create_github_banner(self) -> str:
        """Create GitHub repository banner"""
        
        banner_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 320" width="1280" height="320">
  <defs>
    <linearGradient id="bannerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['bg_deep']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['bg_base']};stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="1280" height="320" fill="url(#bannerGrad)"/>
  
  <!-- Left: Logo -->
  <circle cx="160" cy="160" r="60" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="3" opacity="0.8"/>
  <circle cx="160" cy="160" r="35" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <path d="M160 125 L 160 195" stroke="{self.colors['ownex_gold']}" stroke-width="2" opacity="0.8"/>
  <path d="M125 160 L 195 160" stroke="{self.colors['ownex_gold']}" stroke-width="2" opacity="0.8"/>
  <circle cx="160" cy="160" r="12" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
  
  <!-- Right: Text -->
  <text x="300" y="140" font-family="Arial, sans-serif" font-size="36" font-weight="700" fill="{self.colors['ownex_white']}" letter-spacing="3">OWNEX OMEGA</text>
  <text x="300" y="180" font-family="Arial, sans-serif" font-size="18" font-weight="400" fill="{self.colors['ownex_blue']}" letter-spacing="1">Autonomous Work Operating System</text>
  <text x="300" y="220" font-family="Arial, sans-serif" font-size="14" font-weight="400" fill="{self.colors['ownex_white']}" opacity="0.6">Production v7.0.0</text>
  
  <!-- Accent dots -->
  <circle cx="1100" cy="160" r="4" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="1130" cy="160" r="4" fill="{self.colors['ownex_gold']}" opacity="0.6"/>
  <circle cx="1160" cy="160" r="4" fill="{self.colors['ownex_gold']}" opacity="0.4"/>
</svg>'''
        
        return self._save_asset(banner_svg, "social/ownex-github-banner.svg")

if __name__ == "__main__":
    generator = ProductionGenerator()
    generator.generate_all_production_assets()
    
    # Generate social assets
    print("\nGenerating social media assets...")
    social_path = generator.create_social_preview()
    print(f"  ✓ Social preview: {social_path}")
    
    banner_path = generator.create_github_banner()
    print(f"  ✓ GitHub banner: {banner_path}")
    
    print(f"\n✓ All social assets generated in {generator.output_dir}/social/")