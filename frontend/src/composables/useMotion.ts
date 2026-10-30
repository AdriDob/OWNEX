import { computed, type Ref, ref } from 'vue'

// Motion configuration - integrated with motion.css
export const MOTION_CONFIG = {
  duration: {
    instant: 50,
    fast: 120,
    normal: 200,
    slow: 320,
    slower: 480,
  },
  easing: {
    linear: 'linear',
    smooth: 'cubic-bezier(0.16, 1, 0.3, 1)', // spring-stiff
    spring: 'cubic-bezier(0.16, 1, 0.3, 1)', // spring-gentle
    bounce: 'cubic-bezier(0.34, 1.56, 0.64, 1)', // spring-bounce
    gentle: 'cubic-bezier(0.4, 0, 0.2, 1)', // spring-smooth
    easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
    easeOut: 'cubic-bezier(0, 0, 0.2, 1)',
    easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
  spring: {
    stiff: { damping: 26, stiffness: 300, mass: 1 },
    gentle: { damping: 22, stiffness: 180, mass: 1 },
    bounce: { damping: 16, stiffness: 280, mass: 1 },
    smooth: { damping: 20, stiffness: 150, mass: 1 },
  },
}

// Motion animation classes (matching motion.css)
export const MOTION_CLASSES = {
  // Entrance
  fadeIn: 'ownex-animate-fade-in',
  slideUp: 'ownex-animate-slide-up',
  slideDown: 'ownex-animate-slide-down',
  slideLeft: 'ownex-animate-slide-left',
  slideRight: 'ownex-animate-slide-right',
  scaleIn: 'ownex-animate-scale-in',
  scaleInSpring: 'ownex-animate-scale-in-spring',

  // Exit
  fadeOut: 'ownex-animate-fade-out',
  slideOutUp: 'ownex-animate-slide-out-up',
  slideOutDown: 'ownex-animate-slide-out-down',
  scaleOut: 'ownex-animate-scale-out',

  // Hover
  hoverLift: 'ownex-hover-lift',
  hoverScale: 'ownex-hover-scale',
  hoverGlow: 'ownex-hover-glow',
  activeScale: 'ownex-active-scale',
  focusRing: 'ownex-focus-ring',

  // Loading
  spin: 'ownex-spin',
  pulseSubtle: 'ownex-pulse-subtle',
  pulseGlow: 'ownex-pulse-glow',
  shimmer: 'ownex-shimmer',
  skeleton: 'ownex-skeleton',

  // Transitions
  transition: 'ownex-transition',
  transitionFast: 'ownex-transition-fast',
  transitionSlow: 'ownex-transition-slow',
  transitionSpringStiff: 'ownex-transition-spring-stiff',
  transitionSpringGentle: 'ownex-transition-spring-gentle',
  transitionSpringBounce: 'ownex-transition-spring-bounce',

  // Stagger
  stagger1: 'ownex-stagger-1',
  stagger2: 'ownex-stagger-2',
  stagger3: 'ownex-stagger-3',
  stagger4: 'ownex-stagger-4',
  stagger5: 'ownex-stagger-5',
  stagger6: 'ownex-stagger-6',
}

// Motion hooks
export function useMotion() {
  const isReducedMotion = ref(false)

  // Check for reduced motion preference
  if (typeof window !== 'undefined') {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    isReducedMotion.value = mediaQuery.matches

    mediaQuery.addEventListener('change', (e) => {
      isReducedMotion.value = e.matches
    })
  }

  const getMotionClass = (type: keyof typeof MOTION_CLASSES) => {
    if (isReducedMotion.value) {
      return ''
    }
    return MOTION_CLASSES[type]
  }

  const getTransitionDuration = (duration: keyof typeof MOTION_CONFIG.duration = 'normal') => {
    if (isReducedMotion.value) {
      return '0ms'
    }
    return `${MOTION_CONFIG.duration[duration]}ms`
  }

  const getTransitionEasing = (easing: keyof typeof MOTION_CONFIG.easing = 'smooth') => {
    if (isReducedMotion.value) {
      return 'linear'
    }
    return MOTION_CONFIG.easing[easing]
  }

  const getTransition = (
    duration: keyof typeof MOTION_CONFIG.duration = 'normal',
    easing: keyof typeof MOTION_CONFIG.easing = 'smooth',
  ) => {
    return {
      duration: getTransitionDuration(duration),
      easing: getTransitionEasing(easing),
    }
  }

  const getSpringConfig = (type: keyof typeof MOTION_CONFIG.spring = 'gentle') => {
    return MOTION_CONFIG.spring[type]
  }

  return {
    isReducedMotion,
    getMotionClass,
    getTransitionDuration,
    getTransitionEasing,
    getTransition,
    getSpringConfig,
  }
}

// Specific motion utilities
export function useHoverMotion() {
  const getHoverStyle = () => ({
    transition: 'all 120ms cubic-bezier(0.16, 1, 0.3, 1)',
    transform: 'scale(1.02)',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
  })

  const getClickStyle = () => ({
    transition: 'all 100ms cubic-bezier(0.16, 1, 0.3, 1)',
    transform: 'scale(0.98)',
  })

  const getGlowStyle = () => ({
    transition: 'box-shadow 200ms cubic-bezier(0.16, 1, 0.3, 1)',
    boxShadow: '0 0 0 1px var(--color-primary), 0 0 24px rgba(255, 255, 255, 0.12)',
  })

  return {
    getHoverStyle,
    getClickStyle,
    getGlowStyle,
  }
}

export function useStaggerMotion(count: number, staggerMs: number = 50) {
  const getStaggerDelay = (index: number) => {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return '0ms'
    }
    return `${index * staggerMs}ms`
  }

  const getStaggerClass = (index: number) => {
    if (index === 0) return ''
    if (index === 1) return MOTION_CLASSES.stagger1
    if (index === 2) return MOTION_CLASSES.stagger2
    if (index === 3) return MOTION_CLASSES.stagger3
    if (index === 4) return MOTION_CLASSES.stagger4
    if (index === 5) return MOTION_CLASSES.stagger5
    if (index === 6) return MOTION_CLASSES.stagger6
    return ''
  }

  return {
    getStaggerDelay,
    getStaggerClass,
  }
}

export function useScrollMotion() {
  const getScrollStyle = () => ({
    transition: 'scroll-behavior: smooth',
    scrollPaddingTop: '80px',
  })

  return {
    getScrollStyle,
  }
}

export function usePulseAnimation() {
  const getPulseStyle = () => ({
    animation: 'ownex-pulse-subtle 2s ease-in-out infinite',
  })

  const getPulseGlowStyle = () => ({
    animation: 'ownex-pulse-glow 2s ease-in-out infinite',
  })

  return {
    getPulseStyle,
    getPulseGlowStyle,
  }
}

export function useShimmer() {
  const getShimmerStyle = () => ({
    background:
      'linear-gradient(90deg, var(--color-background) 25%, var(--color-surface) 50%, var(--color-background) 75%)',
    backgroundSize: '200% 100%',
    animation: 'ownex-shimmer 1.5s ease-in-out infinite',
  })

  const getSkeletonStyle = () => ({
    background:
      'linear-gradient(90deg, var(--color-background) 25%, var(--color-surface) 50%, var(--color-background) 75%)',
    backgroundSize: '200% 100%',
    animation: 'ownex-shimmer 1.5s ease-in-out infinite',
    borderRadius: '0.375rem',
  })

  return {
    getShimmerStyle,
    getSkeletonStyle,
  }
}

export function useBounce() {
  const getBounceStyle = () => ({
    animation: 'ownex-bounce-in 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)',
  })

  return {
    getBounceStyle,
  }
}

export function useSpin() {
  const getSpinStyle = () => ({
    animation: 'ownex-spin 1s linear infinite',
  })

  return {
    getSpinStyle,
  }
}

export function useTypewriter() {
  const getTypewriterStyle = () => ({
    animation: 'typewriter 2s steps(40, end)',
  })

  return {
    getTypewriterStyle,
  }
}

// Card animations
export function useCardMotion() {
  const getCardEnterStyle = () => ({
    animation: 'ownex-slide-up 320ms cubic-bezier(0.16, 1, 0.3, 1)',
  })

  const getCardHoverStyle = () => ({
    transition: 'all 120ms cubic-bezier(0.16, 1, 0.3, 1)',
    transform: 'translateY(-2px)',
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
  })

  return {
    getCardEnterStyle,
    getCardHoverStyle,
  }
}

// List animations
export function useListMotion() {
  const getListItemStyle = (index: number) => ({
    animation: `ownex-slide-up 320ms cubic-bezier(0.16, 1, 0.3, 1) ${index * 50}ms`,
  })

  return {
    getListItemStyle,
  }
}

// Modal animations
export function useModalMotion() {
  const getBackdropEnterStyle = () => ({
    animation: 'ownex-modal-backdrop-in 120ms cubic-bezier(0, 0, 0.2, 1)',
  })

  const getBackdropExitStyle = () => ({
    animation: 'ownex-modal-backdrop-out 120ms cubic-bezier(0.4, 0, 1, 1)',
  })

  const getContentEnterStyle = () => ({
    animation: 'ownex-modal-content-in 200ms cubic-bezier(0.16, 1, 0.3, 1)',
  })

  const getContentExitStyle = () => ({
    animation: 'ownex-modal-content-out 120ms cubic-bezier(0.4, 0, 1, 1)',
  })

  return {
    getBackdropEnterStyle,
    getBackdropExitStyle,
    getContentEnterStyle,
    getContentExitStyle,
  }
}

// Toast animations
export function useToastMotion() {
  const getEnterStyle = () => ({
    animation: 'ownex-toast-enter 200ms cubic-bezier(0.16, 1, 0.3, 1)',
  })

  const getExitStyle = () => ({
    animation: 'ownex-toast-exit 120ms cubic-bezier(0.4, 0, 1, 1)',
  })

  return {
    getEnterStyle,
    getExitStyle,
  }
}

// Dropdown animations
export function useDropdownMotion() {
  const getEnterStyle = () => ({
    animation: 'ownex-dropdown-in 120ms cubic-bezier(0.16, 1, 0.3, 1)',
  })

  const getExitStyle = () => ({
    animation: 'ownex-dropdown-out 120ms cubic-bezier(0.4, 0, 1, 1)',
  })

  return {
    getEnterStyle,
    getExitStyle,
  }
}

// Page transitions
export function usePageMotion() {
  const getEnterStyle = () => ({
    animation: 'ownex-page-enter 320ms cubic-bezier(0.16, 1, 0.3, 1)',
  })

  const getExitStyle = () => ({
    animation: 'ownex-page-exit 200ms cubic-bezier(0.4, 0, 1, 1)',
  })

  return {
    getEnterStyle,
    getExitStyle,
  }
}
