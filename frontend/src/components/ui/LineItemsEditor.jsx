import { AnimatePresence, motion } from 'framer-motion'
import { Plus, Trash2 } from 'lucide-react'
import { spring } from '../../lib/motion'
import { Input, Select } from './Field'

/**
 * Reusable dynamic line-item builder used by invoices, purchase orders, journal
 * entries and shipments. Rows animate in/out; a `summary` render-prop draws the
 * totals / balance beneath the grid.
 *
 * Props:
 *  - fields: [{ key, label, type: 'text'|'number'|'select', options?, step?, min?, placeholder?, flex? }]
 *  - value: row[]           (controlled)
 *  - onChange: (rows) => void
 *  - newRow: () => row
 *  - rowExtra?: (row) => ReactNode   (e.g. computed amount shown at row end)
 *  - summary?: (rows) => ReactNode
 *  - addLabel
 */
export default function LineItemsEditor({
  fields,
  value = [],
  onChange,
  newRow,
  rowExtra,
  summary,
  addLabel = 'Add line',
}) {
  const update = (idx, key, v) => {
    const next = value.map((row, i) => (i === idx ? { ...row, [key]: v } : row))
    onChange(next)
  }
  const add = () => onChange([...value, newRow()])
  const remove = (idx) => onChange(value.filter((_, i) => i !== idx))

  return (
    <div className="line-editor">
      <div className="line-head" style={{ gridTemplateColumns: gridCols(fields, !!rowExtra) }}>
        {fields.map((f) => (
          <span key={f.key} className="line-col-label">
            {f.label}
          </span>
        ))}
        {rowExtra && <span className="line-col-label" style={{ textAlign: 'right' }}>Amount</span>}
        <span />
      </div>

      <AnimatePresence initial={false}>
        {value.map((row, idx) => (
          <motion.div
            key={row._key ?? idx}
            className="line-row"
            style={{ gridTemplateColumns: gridCols(fields, !!rowExtra) }}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={spring}
            layout
          >
            {fields.map((f) => (
              <div key={f.key} className="line-cell">
                {f.type === 'select' ? (
                  <Select
                    value={row[f.key] ?? ''}
                    onChange={(e) => update(idx, f.key, e.target.value)}
                  >
                    <option value="">{f.placeholder || 'Select…'}</option>
                    {(f.options || []).map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </Select>
                ) : (
                  <Input
                    type={f.type === 'number' ? 'number' : 'text'}
                    step={f.step}
                    min={f.min}
                    placeholder={f.placeholder}
                    value={row[f.key] ?? ''}
                    onChange={(e) => update(idx, f.key, e.target.value)}
                  />
                )}
              </div>
            ))}
            {rowExtra && <div className="line-cell line-amount">{rowExtra(row)}</div>}
            <button
              type="button"
              className="icon-btn line-remove"
              onClick={() => remove(idx)}
              disabled={value.length <= 1}
              aria-label="Remove line"
            >
              <Trash2 size={15} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>

      <div className="line-foot">
        <button type="button" className="line-add" onClick={add}>
          <Plus size={15} /> {addLabel}
        </button>
        {summary && <div className="line-summary">{summary(value)}</div>}
      </div>
    </div>
  )
}

function gridCols(fields, hasExtra) {
  const cols = fields.map((f) => (f.flex ? `${f.flex}fr` : '1fr'))
  if (hasExtra) cols.push('minmax(90px, 0.7fr)')
  cols.push('36px') // remove button
  return cols.join(' ')
}
