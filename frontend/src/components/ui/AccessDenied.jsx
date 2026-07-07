import { motion } from 'framer-motion'
import { Lock } from 'lucide-react'

/** In-page panel shown when a module returns 403 for the current role. */
export default function AccessDenied({ module = 'this module' }) {
  return (
    <motion.div
      className="access-denied"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="access-icon">
        <Lock size={26} />
      </div>
      <h2>Restricted area</h2>
      <p className="muted">
        Your role doesn’t have access to {module}. Ask an administrator to grant the required
        permission.
      </p>
    </motion.div>
  )
}
