import { motion } from 'framer-motion'
import { Inbox } from 'lucide-react'

/** Friendly placeholder shown when a list has no rows. */
export default function EmptyState({ icon: Icon = Inbox, title = 'Nothing here yet', hint, action }) {
  return (
    <motion.div
      className="empty-state"
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 22 }}
    >
      <div className="empty-icon">
        <Icon size={28} />
      </div>
      <div className="empty-title">{title}</div>
      {hint && <div className="muted">{hint}</div>}
      {action && <div className="empty-action">{action}</div>}
    </motion.div>
  )
}
