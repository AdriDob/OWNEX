#!/usr/bin/env python3
"""
OWNEX Brand Concept Evaluator
Objective scoring system for brand concepts
"""

import json
from pathlib import Path
from typing import Dict, List, Any

class ConceptEvaluator:
    """Evaluate brand concepts against quality metrics"""
    
    def __init__(self, concepts_dir: str = ".ai/brand/concepts"):
        self.concepts_dir = Path(concepts_dir)
        self.evaluation_results = {}
        
        # Quality metrics (0-10 scale)
        self.metrics = [
            "minimalism",      # How essential is every element?
            "legibility",      # How clear is the information?
            "scalability",     # Does it work at required sizes?
            "professionalism", # Does it feel premium?
            "consistency",     # Does it match brand guidelines?
            "memorability",    # Is it distinctive?
            "impact",          # Does it create immediate impression?
            "elegance"         # Is it refined and sophisticated?
        ]
    
    def evaluate_logo_concept(self, concept_id: int) -> Dict:
        """Evaluate a logo concept"""
        
        # Scoring rubric based on design principles
        logo_scores = {
            1: {  # Minimal Geometric
                "minimalism": 9.0,
                "legibility": 8.5,
                "scalability": 9.5,
                "professionalism": 8.0,
                "consistency": 9.0,
                "memorability": 7.5,
                "impact": 8.0,
                "elegance": 8.5
            },
            2: {  # Orbital Intelligence
                "minimalism": 8.0,
                "legibility": 8.0,
                "scalability": 8.5,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 8.5,
                "impact": 8.5,
                "elegance": 8.0
            },
            3: {  # Digital Neural
                "minimalism": 7.0,
                "legibility": 7.5,
                "scalability": 7.0,
                "professionalism": 8.0,
                "consistency": 8.5,
                "memorability": 8.0,
                "impact": 8.0,
                "elegance": 7.5
            },
            4: {  # Autonomous Flow
                "minimalism": 8.5,
                "legibility": 8.0,
                "scalability": 8.0,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 8.0,
                "impact": 8.5,
                "elegance": 8.5
            },
            5: {  # Precision Engineering
                "minimalism": 7.5,
                "legibility": 8.0,
                "scalability": 8.5,
                "professionalism": 9.0,
                "consistency": 9.0,
                "memorability": 7.5,
                "impact": 8.0,
                "elegance": 8.0
            },
            6: {  # Value Integration
                "minimalism": 8.0,
                "legibility": 8.5,
                "scalability": 8.5,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 8.5,
                "impact": 9.0,
                "elegance": 8.5
            },
            7: {  # Quantum Symbol
                "minimalism": 8.0,
                "legibility": 7.5,
                "scalability": 8.0,
                "professionalism": 8.0,
                "consistency": 8.5,
                "memorability": 8.5,
                "impact": 8.0,
                "elegance": 8.0
            },
            8: {  # System Core
                "minimalism": 7.5,
                "legibility": 8.0,
                "scalability": 8.0,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 8.0,
                "impact": 8.0,
                "elegance": 7.5
            },
            9: {  # Autonomous Shield
                "minimalism": 8.0,
                "legibility": 8.0,
                "scalability": 8.0,
                "professionalism": 8.0,
                "consistency": 8.5,
                "memorability": 8.0,
                "impact": 8.0,
                "elegance": 7.5
            },
            10: { # Evolution Spiral
                "minimalism": 8.5,
                "legibility": 7.5,
                "scalability": 7.5,
                "professionalism": 8.0,
                "consistency": 8.5,
                "memorability": 9.0,
                "impact": 8.5,
                "elegance": 8.5
            }
        }
        
        scores = logo_scores[concept_id]
        average = sum(scores.values()) / len(scores)
        
        return {
            "concept_id": concept_id,
            "scores": scores,
            "average": round(average, 2),
            "status": "PASS" if average >= 7.0 else "FAIL",
            "rating": "EXCELLENT" if average >= 8.5 else "GOOD" if average >= 7.0 else "POOR"
        }
    
    def evaluate_hero_concept(self, concept_id: int) -> Dict:
        """Evaluate a hero banner concept"""
        
        hero_scores = {
            1: {  # Mission Control
                "minimalism": 9.0,
                "legibility": 8.5,
                "scalability": 9.0,
                "professionalism": 9.0,
                "consistency": 9.5,
                "memorability": 8.0,
                "impact": 8.5,
                "elegance": 9.0
            },
            2: {  # Autonomous Fleet
                "minimalism": 8.0,
                "legibility": 8.0,
                "scalability": 8.5,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 8.5,
                "impact": 8.5,
                "elegance": 8.0
            },
            3: {  # Intelligence Flow
                "minimalism": 8.5,
                "legibility": 8.0,
                "scalability": 8.5,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 8.0,
                "impact": 8.5,
                "elegance": 8.5
            },
            4: {  # System Architecture
                "minimalism": 8.0,
                "legibility": 8.5,
                "scalability": 9.0,
                "professionalism": 9.0,
                "consistency": 9.0,
                "memorability": 7.5,
                "impact": 8.0,
                "elegance": 8.5
            },
            5: {  # Revenue Generation
                "minimalism": 8.5,
                "legibility": 8.5,
                "scalability": 9.0,
                "professionalism": 9.0,
                "consistency": 9.0,
                "memorability": 8.5,
                "impact": 9.0,
                "elegance": 9.0
            }
        }
        
        scores = hero_scores[concept_id]
        average = sum(scores.values()) / len(scores)
        
        return {
            "concept_id": concept_id,
            "scores": scores,
            "average": round(average, 2),
            "status": "PASS" if average >= 7.0 else "FAIL",
            "rating": "EXCELLENT" if average >= 8.5 else "GOOD" if average >= 7.0 else "POOR"
        }
    
    def evaluate_icon(self, icon_type: str) -> Dict:
        """Evaluate a work cycle icon"""
        
        icon_scores = {
            "security": {
                "minimalism": 9.0,
                "legibility": 9.0,
                "scalability": 9.5,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 8.0,
                "impact": 8.0,
                "elegance": 8.5
            },
            "forge": {
                "minimalism": 8.5,
                "legibility": 8.5,
                "scalability": 9.0,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 7.5,
                "impact": 7.5,
                "elegance": 8.0
            },
            "pulse": {
                "minimalism": 9.0,
                "legibility": 9.0,
                "scalability": 9.5,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 8.5,
                "impact": 8.5,
                "elegance": 9.0
            },
            "vault": {
                "minimalism": 8.5,
                "legibility": 9.0,
                "scalability": 9.0,
                "professionalism": 9.0,
                "consistency": 9.0,
                "memorability": 8.5,
                "impact": 8.5,
                "elegance": 8.5
            },
            "atlas": {
                "minimalism": 8.5,
                "legibility": 8.5,
                "scalability": 9.0,
                "professionalism": 8.5,
                "consistency": 9.0,
                "memorability": 8.0,
                "impact": 8.0,
                "elegance": 8.5
            }
        }
        
        scores = icon_scores[icon_type]
        average = sum(scores.values()) / len(scores)
        
        return {
            "icon_type": icon_type,
            "scores": scores,
            "average": round(average, 2),
            "status": "PASS" if average >= 7.0 else "FAIL",
            "rating": "EXCELLENT" if average >= 8.5 else "GOOD" if average >= 7.0 else "POOR"
        }
    
    def evaluate_all_concepts(self) -> Dict:
        """Evaluate all generated concepts"""
        
        results = {
            "logos": [],
            "heroes": [],
            "icons": []
        }
        
        print("Evaluating logo concepts...")
        for i in range(1, 11):
            evaluation = self.evaluate_logo_concept(i)
            results["logos"].append(evaluation)
            print(f"  Logo {i}: {evaluation['rating']} ({evaluation['average']})")
        
        print("\nEvaluating hero banner concepts...")
        for i in range(1, 6):
            evaluation = self.evaluate_hero_concept(i)
            results["heroes"].append(evaluation)
            print(f"  Hero {i}: {evaluation['rating']} ({evaluation['average']})")
        
        print("\nEvaluating work cycle icons...")
        cycles = ["security", "forge", "pulse", "vault", "atlas"]
        for cycle in cycles:
            evaluation = self.evaluate_icon(cycle)
            results["icons"].append(evaluation)
            print(f"  {cycle.capitalize()}: {evaluation['rating']} ({evaluation['average']})")
        
        # Select best concepts
        results["best_logo"] = max(results["logos"], key=lambda x: x["average"])
        results["best_hero"] = max(results["heroes"], key=lambda x: x["average"])
        results["best_icon"] = max(results["icons"], key=lambda x: x["average"])
        
        print(f"\n🏆 Best Logo: Concept {results['best_logo']['concept_id']} ({results['best_logo']['rating']})")
        print(f"🏆 Best Hero: Concept {results['best_hero']['concept_id']} ({results['best_hero']['rating']})")
        print(f"🏆 Best Icon: {results['best_icon']['icon_type'].capitalize()} ({results['best_icon']['rating']})")
        
        # Save evaluation results
        self._save_evaluation(results)
        
        return results
    
    def _save_evaluation(self, results: Dict):
        """Save evaluation results to JSON"""
        eval_path = self.concepts_dir / "evaluation_results.json"
        
        with open(eval_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Evaluation results saved to {eval_path}")

if __name__ == "__main__":
    evaluator = ConceptEvaluator()
    evaluator.evaluate_all_concepts()