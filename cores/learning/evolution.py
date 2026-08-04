"""Prompt evolution — genetic algorithm for optimizing agent prompts."""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock


@dataclass(slots=True)
class PromptGenome:
    """A prompt genome in the genetic algorithm."""

    id: str
    prompt_template: str
    fitness: float = 0.0
    generation: int = 0
    parent_ids: list[str] = field(default_factory=list)
    mutations: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class PromptEvolutionEngine:
    """
    Genetic algorithm for evolving agent prompts.

    Fitness function evaluates prompt performance on test engagements.
    """

    MUTATION_TYPES = [
        "add_instruction",
        "remove_instruction",
        "modify_instruction",
        "reorder_sections",
        "adjust_temperature",
        "add_example",
        "remove_example",
        "change_persona",
    ]

    MUTATION_RATE = 0.3
    CROSSOVER_RATE = 0.7
    ELITE_SIZE = 2

    def __init__(
        self,
        population_size: int = 20,
        mutation_rate: float = 0.3,
        elite_size: int = 2,
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.elite_size = elite_size
        self._population: list[PromptGenome] = []
        self._fitness_cache: dict[str, float] = {}
        self._evaluation_fn = None
        self._lock = Lock()
        self._generation = 0

    def set_fitness_evaluator(self, fn) -> None:
        """Set the fitness evaluation function.

        fn(prompt: str, test_cases: list[dict]) -> float
        Returns fitness score 0-1.
        """
        self._evaluation_fn = fn

    def initialize_population(self, base_prompts: list[str]) -> None:
        """Initialize population with base prompts + variations."""
        with self._lock:
            self._population = []
            for _i, base in enumerate(base_prompts):
                genome = PromptGenome(
                    id=f"genome_{uuid.uuid4().hex[:8]}",
                    prompt_template=base,
                    generation=0,
                )
                self._population.append(genome)

            # Add variations
            while len(self._population) < self.population_size:
                base = random.choice(base_prompts)
                mutated = self._mutate_prompt(base)
                genome = PromptGenome(
                    id=f"genome_{uuid.uuid4().hex[:8]}",
                    prompt_template=mutated,
                    generation=0,
                    mutations=["initial_variation"],
                )
                self._population.append(genome)

    def evolve(self, test_cases: list[dict]) -> dict:
        """Run one generation of evolution."""
        if not self._evaluation_fn:
            return {"error": "No fitness evaluator set"}

        with self._lock:
            # Evaluate fitness
            for genome in self._population:
                if genome.id not in self._fitness_cache:
                    genome.fitness = self._evaluation_fn(genome.prompt_template, test_cases)
                    self._fitness_cache[genome.id] = genome.fitness
                else:
                    genome.fitness = self._fitness_cache[genome.id]

            # Sort by fitness
            self._population.sort(key=lambda g: g.fitness, reverse=True)

            # Elitism - keep best
            new_population = self._population[: self.elite_size]

            # Generate offspring
            while len(new_population) < self.population_size:
                if random.random() < self.CROSSOVER_RATE and len(self._population) >= 2:
                    parent1 = self._tournament_select()
                    parent2 = self._tournament_select()
                    child_prompt = self._crossover(parent1.prompt_template, parent2.prompt_template)
                else:
                    parent = self._tournament_select()
                    child_prompt = parent.prompt_template

                # Mutate
                if random.random() < self.mutation_rate:
                    child_prompt = self._mutate_prompt(child_prompt)
                    mutations = ["mutation"]
                else:
                    mutations = []

                child = PromptGenome(
                    id=f"genome_{uuid.uuid4().hex[:8]}",
                    prompt_template=child_prompt,
                    generation=self._generation + 1,
                    parent_ids=[p.id for p in [parent1, parent2] if "parent1" in locals()],
                    mutations=mutations,
                )
                new_population.append(child)

            self._population = new_population
            self._generation += 1

            best = self._population[0]
            return {
                "generation": self._generation,
                "best_fitness": best.fitness,
                "avg_fitness": sum(g.fitness for g in self._population) / len(self._population),
                "best_prompt": best.prompt_template[:200] + "..."
                if len(best.prompt_template) > 200
                else best.prompt_template,
            }

    def _tournament_select(self, k: int = 3) -> PromptGenome:
        """Tournament selection."""
        candidates = random.sample(self._population, min(k, len(self._population)))
        return max(candidates, key=lambda g: g.fitness)

    def _crossover(self, prompt1: str, prompt2: str) -> str:
        """Simple crossover: combine sections from both prompts."""
        sections1 = prompt1.split("\n\n")
        sections2 = prompt2.split("\n\n")

        # Take random sections from each
        combined = []
        max_len = max(len(sections1), len(sections2))
        for i in range(max_len):
            if i < len(sections1) and random.random() < 0.5:
                combined.append(sections1[i])
            elif i < len(sections2):
                combined.append(sections2[i])

        return "\n\n".join(combined)

    def _mutate_prompt(self, prompt: str) -> str:
        """Apply random mutation to prompt."""
        mutation = random.choice(self.MUTATION_TYPES)

        if mutation == "add_instruction":
            additions = [
                "\n\nThink step by step before answering.",
                "\n\nBe precise and concise.",
                "\n\nConsider edge cases.",
                "\n\nVerify your reasoning.",
            ]
            return prompt + random.choice(additions)

        elif mutation == "remove_instruction":
            sections = prompt.split("\n\n")
            if len(sections) > 1:
                return "\n\n".join(sections[:-1])
            return prompt

        elif mutation == "modify_instruction":
            # Simple word replacement
            replacements = {
                "analyze": "examine",
                "find": "locate",
                "determine": "assess",
                "comprehensive": "thorough",
                "quickly": "efficiently",
            }
            for old, new in replacements.items():
                if old in prompt and random.random() < 0.3:
                    prompt = prompt.replace(old, new, 1)
            return prompt

        elif mutation == "reorder_sections":
            sections = prompt.split("\n\n")
            if len(sections) > 2:
                random.shuffle(sections)
                return "\n\n".join(sections)
            return prompt

        elif mutation == "adjust_temperature":
            # Add temperature hint
            if "temperature" not in prompt.lower():
                return prompt + "\n\nUse a low temperature (0.1-0.3) for consistent results."
            return prompt

        elif mutation == "add_example":
            return prompt + "\n\nExample: [Input] -> [Expected Output]"

        elif mutation == "remove_example":
            # Remove example sections
            lines = prompt.split("\n")
            filtered = [line for line in lines if not line.strip().startswith("Example:")]
            return "\n".join(filtered)

        elif mutation == "change_persona":
            personas = [
                "You are an expert security researcher.",
                "You are a meticulous bug bounty hunter.",
                "You are a creative exploit developer.",
                "You are a thorough vulnerability analyst.",
            ]
            for p in personas:
                if p in prompt:
                    prompt = prompt.replace(p, random.choice(personas))
                    break
            return prompt

        return prompt

    def get_best(self) -> PromptGenome | None:
        with self._lock:
            if not self._population:
                return None
            return max(self._population, key=lambda g: g.fitness)

    def get_population_stats(self) -> dict:
        with self._lock:
            if not self._population:
                return {"size": 0}
            fitnesses = [g.fitness for g in self._population]
            return {
                "population_size": len(self._population),
                "generation": self._generation,
                "best_fitness": max(fitnesses),
                "avg_fitness": sum(fitnesses) / len(fitnesses),
                "worst_fitness": min(fitnesses),
            }


# Global evolution engine
_evolution_engine = PromptEvolutionEngine()


def initialize_prompt_evolution(base_prompts: list[str], population_size: int = 20) -> None:
    """Initialize the global prompt evolution engine."""
    global _evolution_engine
    _evolution_engine = PromptEvolutionEngine(population_size=population_size)
    _evolution_engine.initialize_population(base_prompts)


def set_prompt_fitness_evaluator(fn) -> None:
    """Set the fitness evaluation function for prompt evolution."""
    _evolution_engine.set_fitness_evaluator(fn)


def evolve_prompts(test_cases: list[dict]) -> dict:
    """Run one generation of prompt evolution."""
    return _evolution_engine.evolve(test_cases)


def get_best_prompt() -> str | None:
    """Get the current best prompt."""
    best = _evolution_engine.get_best()
    return best.prompt_template if best else None


def get_evolution_stats() -> dict:
    return _evolution_engine.get_population_stats()
