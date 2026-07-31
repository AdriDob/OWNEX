#!/usr/bin/env python3
"""
OWNEX Social Media Generator
Create optimized social media images for GitHub, LinkedIn, etc.
"""

from pathlib import Path
from typing import Dict, Any

class SocialMediaGenerator:
    """Generate social media optimized images"""
    
    def __init__(self, output_dir: str = ".ai/brand/approved/social"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Brand colors
        self.colors = {
            "ownex_blue": "#3B82F6",
            "ownex_white": "#F0F0F0",
            "ownex_gold": "#F59E0B",
            "bg_deep": "#050505",
            "bg_base": "#080808",
            "bg_surface": "#0F1117"
        }
    
    def create_github_social_preview(self) -> str:
        """Create GitHub social preview (1200x630)"""
        
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
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  
  <!-- Background -->
  <rect width="1200" height="630" fill="url(#socialGrad)"/>
  <rect width="1200" height="630" fill="url(#socialGrid)"/>
  
  <!-- Logo -->
  <circle cx="600" cy="280" r="100" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="4" opacity="0.8" filter="url(#glow)"/>
  <circle cx="600" cy="280" r="60" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <path d="M600 220 L 600 340" stroke="{self.colors['ownex_gold']}" stroke-width="3" opacity="0.8"/>
  <path d="M540 280 L 660 280" stroke="{self.colors['ownex_gold']}" stroke-width="3" opacity="0.8"/>
  <circle cx="600" cy="280" r="20" fill="{self.colors['ownex_gold']}" opacity="0.9" filter="url(#glow)"/>
  
  <!-- Title -->
  <text x="600" y="450" text-anchor="middle" font-family="Arial, sans-serif" font-size="48" font-weight="700" fill="{self.colors['ownex_white']}" letter-spacing="4">OWNEX OMEGA</text>
  
  <!-- Tagline -->
  <text x="600" y="500" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="400" fill="{self.colors['ownex_blue']}" letter-spacing="2">AUTONOMOUS WORK OPERATING SYSTEM</text>
  
  <!-- Accent line -->
  <line x1="400" y1="530" x2="800" y2="530" stroke="{self.colors['ownex_gold']}" stroke-width="2" opacity="0.6"/>
  
  <!-- Badge -->
  <rect x="1050" y="30" width="120" height="30" rx="15" fill="{self.colors['ownex_blue']}" opacity="0.2" stroke="{self.colors['ownex_blue']}" stroke-width="1"/>
  <text x="1110" y="50" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="600" fill="{self.colors['ownex_white']}" opacity="0.9">v7.0.0</text>
</svg>'''
        
        return self._save_asset(social_svg, "github-social-preview.svg")
    
    def create_linkedin_preview(self) -> str:
        """Create LinkedIn preview (1200x627)"""
        
        linkedin_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 627" width="1200" height="627">
  <defs>
    <linearGradient id="linkedinGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['bg_deep']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['bg_surface']};stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="1200" height="627" fill="url(#linkedinGrad)"/>
  
  <!-- Logo left -->
  <circle cx="200" cy="313" r="120" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="5" opacity="0.8"/>
  <circle cx="200" cy="313" r="70" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <path d="M200 243 L 200 383" stroke="{self.colors['ownex_gold']}" stroke-width="4" opacity="0.8"/>
  <path d="M130 313 L 270 313" stroke="{self.colors['ownex_gold']}" stroke-width="4" opacity="0.8"/>
  <circle cx="200" cy="313" r="25" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
  
  <!-- Text right -->
  <text x="400" y="280" font-family="Arial, sans-serif" font-size="52" font-weight="700" fill="{self.colors['ownex_white']}" letter-spacing="3">OWNEX OMEGA</text>
  <text x="400" y="340" font-family="Arial, sans-serif" font-size="28" font-weight="400" fill="{self.colors['ownex_blue']}" letter-spacing="2">Autonomous Work Operating System</text>
  <text x="400" y="400" font-family="Arial, sans-serif" font-size="20" font-weight="400" fill="{self.colors['ownex_white']}" opacity="0.7">AI • Bug Bounty • Revenue Generation</text>
  
  <!-- Features grid -->
  <g transform="translate(400, 450)">
    <rect x="0" y="0" width="120" height="40" rx="5" fill="{self.colors['ownex_blue']}" opacity="0.15"/>
    <text x="60" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="{self.colors['ownex_white']}" opacity="0.8">AI Agents</text>
    
    <rect x="140" y="0" width="120" height="40" rx="5" fill="{self.colors['ownex_blue']}" opacity="0.15"/>
    <text x="200" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="{self.colors['ownex_white']}" opacity="0.8">Bug Bounty</text>
    
    <rect x="280" y="0" width="120" height="40" rx="5" fill="{self.colors['ownex_blue']}" opacity="0.15"/>
    <text x="340" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="{self.colors['ownex_white']}" opacity="0.8">Revenue</text>
    
    <rect x="420" y="0" width="120" height="40" rx="5" fill="{self.colors['ownex_blue']}" opacity="0.15"/>
    <text x="480" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="{self.colors['ownex_white']}" opacity="0.8">Mobile</text>
    
    <rect x="560" y="0" width="120" height="40" rx="5" fill="{self.colors['ownex_blue']}" opacity="0.15"/>
    <text x="620" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="{self.colors['ownex_white']}" opacity="0.8">Automation</text>
  </g>
</svg>'''
        
        return self._save_asset(linkedin_svg, "linkedin-preview.svg")
    
    def create_twitter_preview(self) -> str:
        """Create Twitter/X preview (1200x600)"""
        
        twitter_svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 600" width="1200" height="600">
  <defs>
    <linearGradient id="twitterGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['bg_deep']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['bg_base']};stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="1200" height="600" fill="url(#twitterGrad)"/>
  
  <!-- Center content -->
  <circle cx="600" cy="250" r="120" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="5" opacity="0.8"/>
  <circle cx="600" cy="250" r="70" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <path d="M600 180 L 600 320" stroke="{self.colors['ownex_gold']}" stroke-width="4" opacity="0.8"/>
  <path d="M530 250 L 670 250" stroke="{self.colors['ownex_gold']}" stroke-width="4" opacity="0.8"/>
  <circle cx="600" cy="250" r="25" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
  
  <!-- Title -->
  <text x="600" y="420" text-anchor="middle" font-family="Arial, sans-serif" font-size="56" font-weight="700" fill="{self.colors['ownex_white']}" letter-spacing="4">OWNEX OMEGA</text>
  
  <!-- Tagline -->
  <text x="600" y="480" text-anchor="middle" font-family="Arial, sans-serif" font-size="28" font-weight="400" fill="{self.colors['ownex_blue']}" letter-spacing="2">Autonomous Work Operating System</text>
  
  <!-- Hashtags -->
  <text x="600" y="540" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" font-weight="400" fill="{self.colors['ownex_white']}" opacity="0.6">#AI #BugBounty #Automation #Dev</text>
</svg>'''
        
        return self._save_asset(twitter_svg, "twitter-preview.svg")
    
    def _save_asset(self, svg_content: str, filename: str) -> str:
        """Save SVG content to file"""
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(svg_content)
        return str(filepath)
    
    def generate_all_social_media(self):
        """Generate all social media images"""
        print("Generating social media images...")
        
        github_path = self.create_github_social_preview()
        print(f"  ✓ GitHub social preview: {github_path}")
        
        linkedin_path = self.create_linkedin_preview()
        print(f"  ✓ LinkedIn preview: {linkedin_path}")
        
        twitter_path = self.create_twitter_preview()
        print(f"  ✓ Twitter/X preview: {twitter_path}")
        
        print(f"\n✓ All social media images generated in {self.output_dir}")
        
        return {
            "github": github_path,
            "linkedin": linkedin_path,
            "twitter": twitter_path
        }

if __name__ == "__main__":
    generator = SocialMediaGenerator()
    generator.generate_all_social_media()