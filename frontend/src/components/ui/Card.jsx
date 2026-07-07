import { motion } from 'framer-motion'
import { fadeUp } from '../../lib/motion'

/** Surface container. `hover` adds a subtle lift; `as` swaps the motion element. */
export default function Card({ children, className = '', hover = false, variant = false, ...rest }) {
  return (
    <motion.div
      className={`card ${variant ? 'card-accent' : ''} ${className}`}
      variants={fadeUp}
      whileHover={hover ? { y: -4 } : undefined}
      transition={{ type: 'spring', stiffness: 300, damping: 26 }}
      {...rest}
    >
      {children}
    </motion.div>
  )
}
