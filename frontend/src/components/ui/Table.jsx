import { motion } from 'framer-motion'
import { staggerContainer } from '../../lib/motion'
import Spinner from './Spinner'
import EmptyState from './EmptyState'

/**
 * Data table with staggered row entrance, plus loading & empty states.
 *
 * Props:
 *  - columns: [{ key, header, render?(row), align?, width?, className? }]
 *  - rows: array
 *  - rowKey: (row, i) => key   (defaults to row.id ?? i)
 *  - loading, empty ({ title, hint, icon, action })
 */
export default function Table({ columns, rows = [], rowKey, loading = false, empty = {} }) {
  const keyOf = rowKey || ((row, i) => row?.id ?? i)

  if (loading) {
    return (
      <div className="table-loading">
        <Spinner />
        <span className="muted">Loading…</span>
      </div>
    )
  }

  if (!rows.length) {
    return <EmptyState {...empty} />
  }

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} style={{ textAlign: c.align || 'left', width: c.width }}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <motion.tbody variants={staggerContainer} initial="hidden" animate="show">
          {rows.map((row, i) => (
            <motion.tr
              key={keyOf(row, i)}
              variants={{
                hidden: { opacity: 0, y: 8 },
                show: { opacity: 1, y: 0 },
              }}
            >
              {columns.map((c) => (
                <td key={c.key} style={{ textAlign: c.align || 'left' }} className={c.className}>
                  {c.render ? c.render(row) : row[c.key]}
                </td>
              ))}
            </motion.tr>
          ))}
        </motion.tbody>
      </table>
    </div>
  )
}
