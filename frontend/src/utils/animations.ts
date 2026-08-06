"""OWNEX Animations System — Unified animations for Tesla/Jarvis style UI.

This system provides smooth, professional animations throughout OWNEX:
- Fade in/out
- Slide transitions
- Scale effects
- Pulse effects
- Glitch effects (for errors)
- Loading animations
- Success animations
- Particle effects

All animations follow Tesla/Jarvis aesthetic: dark, smooth, professional, tech-forward.
"""

from __future__ import annotations

from enum import StrEnum


class AnimationType(StrEnum):
    """Types of animations."""

    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    SLIDE_IN_LEFT = "slide_in_left"
    SLIDE_IN_RIGHT = "slide_in_right"
    SLIDE_IN_UP = "slide_in_up"
    SLIDE_IN_DOWN = "slide_in_down"
    SLIDE_OUT_LEFT = "slide_out_left"
    SLIDE_OUT_RIGHT = "slide_out_right"
    SLIDE_OUT_UP = "slide_out_up"
    SLIDE_OUT_DOWN = "slide_out_down"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"
    PULSE = "pulse"
    GLOW = "glow"
    SHIMMER = "shimmer"
    GLITCH = "glitch"
    SPIN = "spin"
    BOUNCE = "bounce"
    SHAKE = "shake"
    FLIP = "flip"
    ROTATE = "rotate"
    FLOAT = "float"
    DRIFT = "drift"
    WAVE = "wave"
    RIPPLE = "ripple"
    EXPLODE = "explode"
    IMPLODE = "implode"


class AnimationDuration(StrEnum):
    """Animation durations."""

    INSTANT = "0ms"
    FAST = "150ms"
    NORMAL = "300ms"
    SLOW = "500ms"
    VERY_SLOW = "1000ms"


class AnimationEasing(StrEnum):
    """Animation easing functions."""

    LINEAR = "linear"
    EASE_IN = "ease-in"
    EASE_OUT = "ease-out"
    EASE_IN_OUT = "ease-in-out"
    EASE_QUAD_IN = "cubic-bezier(0.55, 0.085, 0.68, 0.53)"
    EASE_QUAD_OUT = "cubic-bezier(0.25, 0.46, 0.45, 0.94)"
    EASE_QUAD_IN_OUT = "cubic-bezier(0.455, 0.03, 0.515, 0.955)"
    EASE_CUBIC_IN = "cubic-bezier(0.55, 0.055, 0.675, 0.19)"
    EASE_CUBIC_OUT = "cubic-bezier(0.215, 0.61, 0.355, 1)"
    EASE_CUBIC_IN_OUT = "cubic-bezier(0.645, 0.045, 0.355, 1)"
    EASE_ELASTIC_OUT = "cubic-bezier(0.175, 0.885, 0.32, 1.275)"
    EASE_BACK_OUT = "cubic-bezier(0.34, 1.56, 0.64, 1)"


class AnimationConfig:
    """Configuration for an animation."""

    def __init__(
        self,
        type: AnimationType,
        duration: AnimationDuration = AnimationDuration.NORMAL,
        easing: AnimationEasing = AnimationEasing.EASE_IN_OUT,
        delay: str = "0ms",
        iterations: str = "1",
        direction: str = "normal",
        fill_mode: str = "forwards",
    ):
        self.type = type
        self.duration = duration
        self.easing = easing
        self.delay = delay
        self.iterations = iterations
        self.direction = direction
        self.fill_mode = fill_mode

    def to_css(self) -> str:
        """Convert to CSS animation string."""
        return f"{self.type} {self.duration} {self.easing} {self.delay} {self.iterations} {self.direction} {self.fill_mode}"


# Predefined animation configs
ANIMATIONS = {
    "fade_in": AnimationConfig(AnimationType.FADE_IN, AnimationDuration.NORMAL, AnimationEasing.EASE_IN_OUT),
    "fade_out": AnimationConfig(AnimationType.FADE_OUT, AnimationDuration.NORMAL, AnimationEasing.EASE_IN_OUT),
    "slide_in_left": AnimationConfig(AnimationType.SLIDE_IN_LEFT, AnimationDuration.NORMAL, AnimationEasing.EASE_CUBIC_OUT),
    "slide_in_right": AnimationConfig(AnimationType.SLIDE_IN_RIGHT, AnimationDuration.NORMAL, AnimationEasing.EASE_CUBIC_OUT),
    "slide_in_up": AnimationConfig(AnimationType.SLIDE_IN_UP, AnimationDuration.NORMAL, AnimationEasing.EASE_CUBIC_OUT),
    "slide_in_down": AnimationConfig(AnimationType.SLIDE_IN_DOWN, AnimationDuration.NORMAL, AnimationEasing.EASE_CUBIC_OUT),
    "scale_in": AnimationConfig(AnimationType.SCALE_IN, AnimationDuration.NORMAL, AnimationEasing.EASE_ELASTIC_OUT),
    "scale_out": AnimationConfig(AnimationType.SCALE_OUT, AnimationDuration.NORMAL, AnimationEasing.EASE_IN_OUT),
    "pulse": AnimationConfig(AnimationType.PULSE, AnimationDuration.SLOW, AnimationEasing.EASE_IN_OUT, iterations="infinite"),
    "glow": AnimationConfig(AnimationType.GLOW, AnimationDuration.SLOW, AnimationEasing.EASE_IN_OUT, iterations="infinite"),
    "shimmer": AnimationConfig(AnimationType.SHIMMER, AnimationDuration.VERY_SLOW, AnimationEasing.LINEAR, iterations="infinite"),
    "glitch": AnimationConfig(AnimationType.GLITCH, AnimationDuration.FAST, AnimationEasing.STEPS, iterations="3"),
    "spin": AnimationConfig(AnimationType.SPIN, AnimationDuration.SLOW, AnimationEasing.LINEAR, iterations="infinite"),
    "bounce": AnimationConfig(AnimationType.BOUNCE, AnimationDuration.NORMAL, AnimationEasing.EASE_BACK_OUT, iterations="2"),
    "shake": AnimationConfig(AnimationType.SHAKE, AnimationDuration.FAST, AnimationEasing.EASE_IN_OUT, iterations="3"),
    "float": AnimationConfig(AnimationType.FLOAT, AnimationDuration.SLOW, AnimationEasing.EASE_IN_OUT, iterations="infinite"),
    "drift": AnimationConfig(AnimationType.DRIFT, AnimationDuration.VERY_SLOW, AnimationEasing.LINEAR, iterations="infinite"),
    "ripple": AnimationConfig(AnimationType.RIPPLE, AnimationDuration.NORMAL, AnimationEasing.EASE_OUT),
    "explode": AnimationConfig(AnimationType.EXPLODE, AnimationDuration.NORMAL, AnimationEasing.EASE_ELASTIC_OUT),
    "implode": AnimationConfig(AnimationType.IMPLODE, AnimationDuration.NORMAL, AnimationEasing.EASE_CUBIC_IN),
}


def get_animation(name: str) -> AnimationConfig:
    """Get a predefined animation by name."""
    return ANIMATIONS.get(name, ANIMATIONS["fade_in"])


def get_animation_css(name: str) -> str:
    """Get CSS animation string for a predefined animation."""
    return get_animation(name).to_css()
