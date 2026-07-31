#!/usr/bin/env python3
"""
OWNEX Brand SVG Generator
Fast programmatic SVG generation for brand concepts
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Tuple
import math

class OwnexSVGGenerator:
    """Generate OWNEX OMEGA brand assets programmatically"""
    
    def __init__(self, output_dir: str = ".ai/brand/concepts"):
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
            "bg_elevated": "#14161E",
            "status_success": "#22C55E",
            "status_error": "#EF4444",
            "status_warn": "#F59E0B"
        }
    
    def generate_logo_concept(self, concept_id: int, style: str) -> str:
        """Generate a logo concept SVG"""
        
        concepts = {
            1: self._logo_minimal_geometric,
            2: self._logo_orbital_intelligence,
            3: self._logo_digital_neural,
            4: self._logo_autonomous_flow,
            5: self._logo_precision_engineering,
            6: self._logo_value_integration,
            7: self._logo_quantum_symbol,
            8: self._logo_system_core,
            9: self._logo_autonomous_shield,
            10: self._logo_evolution_spiral
        }
        
        svg_content = concepts[concept_id](style)
        return self._save_svg(svg_content, f"logos/logo_concept_{concept_id}_{style}.svg")
    
    def _logo_minimal_geometric(self, style: str) -> str:
        """Ultra-minimalist logo with single continuous line"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:0.6" />
    </linearGradient>
  </defs>
  <circle cx="100" cy="100" r="80" fill="none" stroke="url(#grad1)" stroke-width="3" opacity="0.9"/>
  <circle cx="100" cy="100" r="60" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.6"/>
  <circle cx="100" cy="100" r="40" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <circle cx="135" cy="65" r="8" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def _logo_orbital_intelligence(self, style: str) -> str:
        """Logo with orbital rings suggesting intelligence"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="orbitalGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['ownex_white']};stop-opacity:0.8" />
    </linearGradient>
  </defs>
  <circle cx="100" cy="100" r="50" fill="url(#orbitalGrad)" opacity="0.9"/>
  <ellipse cx="100" cy="100" rx="70" ry="25" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.7" transform="rotate(0 100 100)"/>
  <ellipse cx="100" cy="100" rx="70" ry="25" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.5" transform="rotate(60 100 100)"/>
  <ellipse cx="100" cy="100" rx="70" ry="25" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.3" transform="rotate(120 100 100)"/>
  <circle cx="140" cy="60" r="6" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def _logo_digital_neural(self, style: str) -> str:
        """Logo formed by interconnected nodes"""
        nodes = [
            (100, 50), (50, 100), (150, 100), (100, 150),
            (70, 70), (130, 70), (70, 130), (130, 130)
        ]
        
        connections = [
            (0, 4), (0, 5), (1, 4), (1, 6), (2, 5), (2, 7), (3, 6), (3, 7),
            (4, 5), (6, 7), (4, 6), (5, 7)
        ]
        
        svg_lines = []
        for i, j in connections:
            x1, y1 = nodes[i]
            x2, y2 = nodes[j]
            svg_lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{self.colors["ownex_blue"]}" stroke-width="1.5" opacity="0.6"/>')
        
        svg_circles = []
        for i, (x, y) in enumerate(nodes):
            if i == 0:
                svg_circles.append(f'<circle cx="{x}" cy="{y}" r="12" fill="{self.colors["ownex_blue"]}" opacity="0.9"/>')
            else:
                svg_circles.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{self.colors["ownex_blue"]}" opacity="0.7"/>')
        
        svg_circles.append(f'<circle cx="145" cy="55" r="5" fill="{self.colors["ownex_gold"]}" opacity="0.9"/>')
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <rect width="200" height="200" fill="{self.colors["bg_deep"]}"/>
  {chr(10).join(svg_lines)}
  {chr(10).join(svg_circles)}
</svg>'''
    
    def _logo_autonomous_flow(self, style: str) -> str:
        """Logo with flowing lines suggesting continuous operation"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="flowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
      <stop offset="50%" style="stop-color:{self.colors['ownex_white']};stop-opacity:0.8" />
      <stop offset="100%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
    </linearGradient>
  </defs>
  <circle cx="100" cy="100" r="70" fill="none" stroke="url(#flowGrad)" stroke-width="4" opacity="0.8"/>
  <path d="M100 30 Q 150 50 170 100 Q 150 150 100 170 Q 50 150 30 100 Q 50 50 100 30" 
        fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.6"/>
  <circle cx="100" cy="100" r="35" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <circle cx="130" cy="70" r="7" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def _logo_precision_engineering(self, style: str) -> str:
        """Technical logo with construction lines"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="0.5" opacity="0.2"/>
    </pattern>
  </defs>
  <rect width="200" height="200" fill="url(#grid)"/>
  <circle cx="100" cy="100" r="60" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="3"/>
  <circle cx="100" cy="100" r="40" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.7"/>
  <circle cx="100" cy="100" r="20" fill="{self.colors['ownex_blue']}" opacity="0.9"/>
  <line x1="100" y1="40" x2="100" y2="160" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.5"/>
  <line x1="40" y1="100" x2="160" y2="100" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.5"/>
  <circle cx="100" cy="40" r="3" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def _logo_value_integration(self, style: str) -> str:
        """Logo with gold accent for value"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="valueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
      <stop offset="70%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:0.8" />
      <stop offset="100%" style="stop-color:{self.colors['ownex_gold']};stop-opacity:1" />
    </linearGradient>
  </defs>
  <circle cx="100" cy="100" r="70" fill="none" stroke="url(#valueGrad)" stroke-width="4"/>
  <circle cx="100" cy="100" r="45" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <path d="M100 55 L 100 145 M 55 100 L 145 100" stroke="{self.colors['ownex_gold']}" stroke-width="3" opacity="0.8"/>
  <circle cx="100" cy="100" r="15" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def _logo_quantum_symbol(self, style: str) -> str:
        """Abstract quantum-like overlapping rings"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  <circle cx="100" cy="100" r="60" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="3" opacity="0.8" filter="url(#glow)"/>
  <circle cx="100" cy="100" r="50" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.5"/>
  <circle cx="100" cy="100" r="40" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.3"/>
  <circle cx="100" cy="100" r="25" fill="{self.colors['ownex_blue']}" opacity="0.9"/>
  <circle cx="135" cy="65" r="6" fill="{self.colors['ownex_gold']}" opacity="0.9" filter="url(#glow)"/>
</svg>'''
    
    def _logo_system_core(self, style: str) -> str:
        """Central core with radiating elements"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <circle cx="100" cy="100" r="40" fill="{self.colors['ownex_blue']}" opacity="0.9"/>
  <line x1="100" y1="60" x2="100" y2="30" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.7"/>
  <line x1="100" y1="140" x2="100" y2="170" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.7"/>
  <line x1="60" y1="100" x2="30" y2="100" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.7"/>
  <line x1="140" y1="100" x2="170" y2="100" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.7"/>
  <line x1="72" y1="72" x2="50" y2="50" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.5"/>
  <line x1="128" y1="72" x2="150" y2="50" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.5"/>
  <line x1="72" y1="128" x2="50" y2="150" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.5"/>
  <line x1="128" y1="128" x2="150" y2="150" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.5"/>
  <circle cx="100" cy="100" r="15" fill="{self.colors['ownex_white']}" opacity="0.9"/>
  <circle cx="135" cy="65" r="5" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def _logo_autonomous_shield(self, style: str) -> str:
        """Protective shield elements"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <path d="M100 30 L 160 50 L 160 100 Q 160 150 100 170 Q 40 150 40 100 L 40 50 Z" 
        fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="3" opacity="0.8"/>
  <circle cx="100" cy="90" r="30" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <path d="M100 60 L 100 120 M 70 90 L 130 90" stroke="{self.colors['ownex_white']}" stroke-width="2" opacity="0.9"/>
  <circle cx="145" cy="55" r="5" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def _logo_evolution_spiral(self, style: str) -> str:
        """Golden ratio spiral suggesting evolution"""
        points = []
        for i in range(0, 360, 15):
            angle = math.radians(i)
            radius = 20 + i * 0.15
            x = 100 + radius * math.cos(angle)
            y = 100 + radius * math.sin(angle)
            points.append(f"{x},{y}")
        
        point_str = " ".join(points)
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="spiralGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['ownex_blue']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['ownex_gold']};stop-opacity:1" />
    </linearGradient>
  </defs>
  <polyline points="{point_str}" fill="none" stroke="url(#spiralGrad)" stroke-width="3" opacity="0.8"/>
  <circle cx="100" cy="100" r="25" fill="{self.colors['ownex_blue']}" opacity="0.9"/>
  <circle cx="100" cy="100" r="10" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def generate_hero_banner(self, concept_id: int) -> str:
        """Generate hero banner concept"""
        
        concepts = {
            1: self._hero_mission_control,
            2: self._hero_autonomous_fleet,
            3: self._hero_intelligence_flow,
            4: self._hero_system_architecture,
            5: self._hero_revenue_generation
        }
        
        svg_content = concepts[concept_id]()
        return self._save_svg(svg_content, f"heroes/hero_concept_{concept_id}.svg")
    
    def _hero_mission_control(self) -> str:
        """Mission Control dashboard interface"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <rect width="1920" height="1080" fill="{self.colors['bg_deep']}"/>
  
  <!-- Subtle grid pattern -->
  <defs>
    <pattern id="heroGrid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="0.5" opacity="0.1"/>
    </pattern>
  </defs>
  <rect width="1920" height="1080" fill="url(#heroGrid)"/>
  
  <!-- Central hero circle -->
  <circle cx="960" cy="540" r="200" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.3"/>
  <circle cx="960" cy="540" r="150" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="1.5" opacity="0.2"/>
  <circle cx="960" cy="540" r="100" fill="{self.colors['ownex_blue']}" opacity="0.1"/>
  
  <!-- Data flow lines -->
  <line x1="200" y1="540" x2="760" y2="540" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  <line x1="1160" y1="540" x2="1720" y2="540" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  <line x1="960" y1="200" x2="960" y2="440" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  <line x1="960" y1="640" x2="960" y2="880" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  
  <!-- Accent dots -->
  <circle cx="760" cy="540" r="4" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="1160" cy="540" r="4" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="960" cy="440" r="4" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="960" cy="640" r="4" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  
  <!-- Text placeholder -->
  <text x="960" y="950" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" fill="{self.colors['ownex_white']}" opacity="0.6">OWNEX OMEGA</text>
  <text x="960" y="980" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" fill="{self.colors['ownex_blue']}" opacity="0.8">Autonomous Work Operating System</text>
</svg>'''
    
    def _hero_autonomous_fleet(self) -> str:
        """Autonomous fleet visualization"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <rect width="1920" height="1080" fill="{self.colors['bg_deep']}"/>
  
  <!-- Agent nodes -->
  <circle cx="400" cy="300" r="40" fill="{self.colors['ownex_blue']}" opacity="0.6"/>
  <circle cx="800" cy="250" r="35" fill="{self.colors['ownex_blue']}" opacity="0.5"/>
  <circle cx="1200" cy="350" r="45" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <circle cx="600" cy="500" r="38" fill="{self.colors['ownex_blue']}" opacity="0.55"/>
  <circle cx="1000" cy="480" r="42" fill="{self.colors['ownex_blue']}" opacity="0.65"/>
  <circle cx="1400" cy="520" r="36" fill="{self.colors['ownex_blue']}" opacity="0.5"/>
  <circle cx="500" cy="700" r="40" fill="{self.colors['ownex_blue']}" opacity="0.6"/>
  <circle cx="900" cy="750" r="35" fill="{self.colors['ownex_blue']}" opacity="0.5"/>
  <circle cx="1300" cy="680" r="44" fill="{self.colors['ownex_blue']}" opacity="0.68"/>
  
  <!-- Connection lines -->
  <line x1="400" y1="300" x2="800" y2="250" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  <line x1="800" y1="250" x2="1200" y2="350" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  <line x1="600" y1="500" x2="1000" y2="480" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  <line x1="1000" y1="480" x2="1400" y2="520" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  <line x1="500" y1="700" x2="900" y2="750" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  <line x1="900" y1="750" x2="1300" y2="680" stroke="{self.colors['ownex_blue']}" stroke-width="1" opacity="0.3"/>
  
  <!-- Central coordination -->
  <circle cx="960" cy="540" r="60" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <circle cx="960" cy="540" r="30" fill="{self.colors['ownex_white']}" opacity="0.9"/>
  
  <!-- Gold accents -->
  <circle cx="960" cy="540" r="8" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def _hero_intelligence_flow(self) -> str:
        """Data flow visualization"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <rect width="1920" height="1080" fill="{self.colors['bg_deep']}"/>
  
  <!-- Flow paths -->
  <path d="M100 540 Q 400 300 960 540 Q 1520 780 1820 540" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="3" opacity="0.4"/>
  <path d="M100 540 Q 400 780 960 540 Q 1520 300 1820 540" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.3"/>
  
  <!-- Data points -->
  <circle cx="400" cy="300" r="15" fill="{self.colors['ownex_blue']}" opacity="0.6"/>
  <circle cx="400" cy="780" r="15" fill="{self.colors['ownex_blue']}" opacity="0.6"/>
  <circle cx="1520" cy="300" r="15" fill="{self.colors['ownex_blue']}" opacity="0.6"/>
  <circle cx="1520" cy="780" r="15" fill="{self.colors['ownex_blue']}" opacity="0.6"/>
  
  <!-- Central processing -->
  <circle cx="960" cy="540" r="80" fill="{self.colors['ownex_blue']}" opacity="0.2"/>
  <circle cx="960" cy="540" r="50" fill="{self.colors['ownex_blue']}" opacity="0.4"/>
  <circle cx="960" cy="540" r="25" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  
  <!-- Value highlights -->
  <circle cx="960" cy="540" r="10" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
  <circle cx="400" cy="300" r="5" fill="{self.colors['ownex_gold']}" opacity="0.7"/>
  <circle cx="1520" cy="780" r="5" fill="{self.colors['ownex_gold']}" opacity="0.7"/>
</svg>'''
    
    def _hero_system_architecture(self) -> str:
        """System architecture diagram"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <rect width="1920" height="1080" fill="{self.colors['bg_deep']}"/>
  
  <!-- Architecture layers -->
  <rect x="200" y="150" width="1520" height="120" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.4" rx="10"/>
  <rect x="200" y="350" width="1520" height="120" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.4" rx="10"/>
  <rect x="200" y="550" width="1520" height="120" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.4" rx="10"/>
  <rect x="200" y="750" width="1520" height="120" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.4" rx="10"/>
  
  <!-- Layer connections -->
  <line x1="960" y1="270" x2="960" y2="350" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.5"/>
  <line x1="960" y1="470" x2="960" y2="550" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.5"/>
  <line x1="960" y1="670" x2="960" y2="750" stroke="{self.colors['ownex_blue']}" stroke-width="2" opacity="0.5"/>
  
  <!-- Central core -->
  <circle cx="960" cy="540" r="40" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <circle cx="960" cy="540" r="20" fill="{self.colors['ownex_white']}" opacity="0.9"/>
  
  <!-- Accent points -->
  <circle cx="960" cy="210" r="6" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="960" cy="410" r="6" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="960" cy="610" r="6" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
  <circle cx="960" cy="810" r="6" fill="{self.colors['ownex_gold']}" opacity="0.8"/>
</svg>'''
    
    def _hero_revenue_generation(self) -> str:
        """Revenue generation visualization"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <rect width="1920" height="1080" fill="{self.colors['bg_deep']}"/>
  
  <!-- Growth chart -->
  <polyline points="200,800 400,750 600,700 800,650 1000,550 1200,450 1400,350 1600,250 1720,200" 
            fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="3" opacity="0.6"/>
  
  <!-- Area under curve -->
  <polygon points="200,800 400,750 600,700 800,650 1000,550 1200,450 1400,350 1600,250 1720,200 1720,900 200,900" 
           fill="{self.colors['ownex_blue']}" opacity="0.1"/>
  
  <!-- Data points -->
  <circle cx="400" cy="750" r="8" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <circle cx="600" cy="700" r="8" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <circle cx="800" cy="650" r="8" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
  <circle cx="1000" cy="550" r="10" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <circle cx="1200" cy="450" r="10" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <circle cx="1400" cy="350" r="10" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
  <circle cx="1600" cy="250" r="12" fill="{self.colors['ownex_blue']}" opacity="0.9"/>
  <circle cx="1720" cy="200" r="12" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
  
  <!-- Central highlight -->
  <circle cx="960" cy="540" r="100" fill="{self.colors['ownex_blue']}" opacity="0.15"/>
  <circle cx="960" cy="540" r="50" fill="{self.colors['ownex_blue']}" opacity="0.3"/>
</svg>'''
    
    def generate_icon(self, icon_type: str, cycle: str) -> str:
        """Generate work cycle icon"""
        
        icons = {
            "security": self._icon_security,
            "forge": self._icon_forge,
            "pulse": self._icon_pulse,
            "vault": self._icon_vault,
            "atlas": self._icon_atlas
        }
        
        svg_content = icons[icon_type]()
        return self._save_svg(svg_content, f"icons/{cycle}_{icon_type}.svg")
    
    def _icon_security(self) -> str:
        """Security cycle icon - shield"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <path d="M32 8 L 56 16 L 56 32 Q 56 48 32 56 Q 8 48 8 32 L 8 16 Z" 
        fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2.5" opacity="0.9"/>
  <circle cx="32" cy="32" r="10" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
</svg>'''
    
    def _icon_forge(self) -> str:
        """Forge cycle icon - hammer/anvil"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect x="16" y="28" width="32" height="8" fill="{self.colors['ownex_blue']}" opacity="0.8" rx="2"/>
  <rect x="28" y="20" width="8" height="24" fill="{self.colors['ownex_blue']}" opacity="0.9" rx="1"/>
  <circle cx="32" cy="44" r="6" fill="{self.colors['ownex_blue']}" opacity="0.7"/>
</svg>'''
    
    def _icon_pulse(self) -> str:
        """Pulse cycle icon - heartbeat"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <polyline points="8,32 20,32 28,20 36,44 44,32 56,32" 
            fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2.5" opacity="0.9"/>
  <circle cx="32" cy="32" r="4" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
</svg>'''
    
    def _icon_vault(self) -> str:
        """Vault cycle icon - bank/vault"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect x="12" y="16" width="40" height="32" fill="none" stroke="{self.colors['ownex_gold']}" stroke-width="2.5" opacity="0.9" rx="4"/>
  <circle cx="32" cy="32" r="8" fill="none" stroke="{self.colors['ownex_gold']}" stroke-width="2" opacity="0.8"/>
  <circle cx="32" cy="32" r="3" fill="{self.colors['ownex_gold']}" opacity="0.9"/>
</svg>'''
    
    def _icon_atlas(self) -> str:
        """Atlas cycle icon - globe/intelligence"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <circle cx="32" cy="32" r="20" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="2.5" opacity="0.9"/>
  <ellipse cx="32" cy="32" rx="20" ry="8" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="1.5" opacity="0.6"/>
  <ellipse cx="32" cy="32" rx="8" ry="20" fill="none" stroke="{self.colors['ownex_blue']}" stroke-width="1.5" opacity="0.6"/>
  <circle cx="32" cy="32" r="4" fill="{self.colors['ownex_blue']}" opacity="0.8"/>
</svg>'''
    
    def _save_svg(self, svg_content: str, filename: str) -> str:
        """Save SVG content to file"""
        filepath = self.output_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(svg_content)
        
        return str(filepath)
    
    def generate_all_concepts(self):
        """Generate all brand concepts"""
        print("Generating OWNEX OMEGA brand concepts...")
        
        # Generate 10 logo concepts
        print("Generating 10 logo concepts...")
        for i in range(1, 11):
            self.generate_logo_concept(i, "primary")
            print(f"  ✓ Logo concept {i} generated")
        
        # Generate 5 hero banner concepts
        print("Generating 5 hero banner concepts...")
        for i in range(1, 6):
            self.generate_hero_banner(i)
            print(f"  ✓ Hero banner concept {i} generated")
        
        # Generate 5 work cycle icons
        print("Generating 5 work cycle icons...")
        cycles = ["security", "forge", "pulse", "vault", "atlas"]
        for cycle in cycles:
            self.generate_icon(cycle, cycle)
            print(f"  ✓ {cycle.capitalize()} icon generated")
        
        print(f"\n✓ All concepts generated in {self.output_dir}")
        return str(self.output_dir)

if __name__ == "__main__":
    generator = OwnexSVGGenerator()
    generator.generate_all_concepts()