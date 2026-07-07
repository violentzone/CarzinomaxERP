import { useEffect } from 'react'
import { motion, useMotionValue, useTransform, animate, useReducedMotion } from 'framer-motion'
import { fadeUp } from '../../lib/motion'

/**
 * KPI tile with an animated count-up value.
 *
 * Props:
 *  - value: the target number
 *  - format: (n) => string  (e.g. currency)
 *  - label, icon, hint, trend ('up' | 'down')
 */
export default function StatCard({ value = 0, format = (n) => Math.round(n).toString(), label, icon: Icon, hint, accent = 0 }) {
  const reduce = useReducedMotion()
  const mv = useMotionValue(0)
  const text = useTransform(mv, (v) => format(v))

  useEffect(() => {
    if (reduce) {
      mv.set(value)
      return
    }
    const controls = animate(mv, value, { duration: 1, ease: [0.22, 1, 0.36, 1] })
    return controls.stop
  }, [value, mv, reduce])

  return (
    <motion.div className="stat-card card" variants={fadeUp} whileHover={{ y: -4 }}>
      <div className={`stat-icon stat-icon-${accent % 4}`}>{Icon && <Icon size={20} />}</div>
      <div className="stat-body">
        <div className="stat-label">{label}</div>
        <motion.div className="stat-value">{text}</motion.div>
        {hint && <div className="stat-hint muted">{hint}</div>}
      </div>
    </motion.div>
  )
}
