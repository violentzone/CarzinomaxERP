import { motion } from 'framer-motion'

/** Minimal circular spinner. */
export default function Spinner({ size = 20, className = '' }) {
  return (
    <motion.span
      className={`spinner ${className}`}
      style={{ width: size, height: size }}
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, ease: 'linear', duration: 0.8 }}
      role="status"
      aria-label="Loading"
    />
  )
}
