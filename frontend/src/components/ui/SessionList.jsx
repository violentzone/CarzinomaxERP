import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'

/**
 * "Created this session" list for POST-only resources (payments, journal
 * entries, leaves, paychecks, shipments, purchase orders) — the backend has no
 * GET for these, so we show what was created since the page loaded. Cleared on
 * reload. `columns` matches the <Table> column shape.
 */
export default function SessionList({ items = [], columns, title = 'Created this session' }) {
  if (!items.length) return null
  return (
    <motion.div className="session-list" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="session-head">
        <Sparkles size={15} />
        <span>{title}</span>
        <span className="session-badge">{items.length}</span>
        <span className="muted session-note">not persisted to a list endpoint — clears on refresh</span>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} style={{ textAlign: c.align || 'left' }}>
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((row, i) => (
              <motion.tr
                key={row.id ?? i}
                initial={{ opacity: 0, backgroundColor: 'rgba(170,59,255,0.12)' }}
                animate={{ opacity: 1, backgroundColor: 'rgba(170,59,255,0)' }}
                transition={{ duration: 1.2 }}
              >
                {columns.map((c) => (
                  <td key={c.key} style={{ textAlign: c.align || 'left' }}>
                    {c.render ? c.render(row) : row[c.key]}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  )
}
