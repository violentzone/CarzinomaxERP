import { motion } from 'framer-motion'

/** Standard page title block with optional subtitle and right-aligned actions. */
export default function PageHeader({ title, subtitle, icon: Icon, actions }) {
  return (
    <motion.div
      className="page-header"
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="page-header-title">
        {Icon && (
          <span className="page-header-icon">
            <Icon size={22} />
          </span>
        )}
        <div>
          <h1>{title}</h1>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="page-header-actions row gap-2">{actions}</div>}
    </motion.div>
  )
}
