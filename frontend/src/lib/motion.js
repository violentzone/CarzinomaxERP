/**
 * Shared Framer Motion variants and springs, so motion feels consistent across
 * the app. Components gate these behind `useReducedMotion()` where relevant.
 */

export const spring = { type: 'spring', stiffness: 380, damping: 30 }
export const softSpring = { type: 'spring', stiffness: 220, damping: 26 }

/** Page-level transition used by the router outlet. */
export const pageVariants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.32, ease: [0.22, 1, 0.36, 1] } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.18 } },
}

/** Container that staggers its children in on mount. */
export const staggerContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05, delayChildren: 0.04 } },
}

export const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
}

export const scaleIn = {
  hidden: { opacity: 0, scale: 0.96 },
  show: { opacity: 1, scale: 1, transition: spring },
}

/** Modal + backdrop. */
export const backdropVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1 },
}

export const modalVariants = {
  hidden: { opacity: 0, scale: 0.94, y: 16 },
  show: { opacity: 1, scale: 1, y: 0, transition: spring },
  exit: { opacity: 0, scale: 0.96, y: 8, transition: { duration: 0.15 } },
}
