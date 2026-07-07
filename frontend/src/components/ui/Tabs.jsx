import { motion } from 'framer-motion'

/**
 * Horizontal tab bar with an animated active underline (shared layoutId).
 *
 * Props:
 *  - tabs: [{ key, label, icon? }]
 *  - active: key
 *  - onChange: (key) => void
 *  - idBase: unique layout id namespace (so multiple tab bars don't collide)
 */
export default function Tabs({ tabs, active, onChange, idBase = 'tabs' }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => {
        const isActive = t.key === active
        const Icon = t.icon
        return (
          <button
            key={t.key}
            role="tab"
            aria-selected={isActive}
            className={`tab ${isActive ? 'tab-active' : ''}`}
            onClick={() => onChange(t.key)}
          >
            {Icon && <Icon size={16} />}
            <span>{t.label}</span>
            {isActive && (
              <motion.span
                className="tab-underline"
                layoutId={`${idBase}-underline`}
                transition={{ type: 'spring', stiffness: 400, damping: 32 }}
              />
            )}
          </button>
        )
      })}
    </div>
  )
}
