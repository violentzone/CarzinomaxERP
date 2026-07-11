/* eslint-disable react-refresh/only-export-components -- form helpers are colocated with the form component by design */
import { Field, Input, Select, Textarea } from './ui/Field'
import { num } from '../lib/format'

/**
 * Render a controlled form from a field schema. Kept intentionally small — the
 * parent owns `values` and gets changes via `setField`.
 *
 * Field: { key, label, type, options?, required?, placeholder?, step?, min?,
 *          hint?, full?(span both cols), default?, nullable?, disabled? }
 * type: 'text' | 'number' | 'email' | 'date' | 'datetime-local' | 'select' | 'textarea'
 */
export function SchemaForm({ fields, values, setField }) {
  return (
    <div className="form-grid">
      {fields.map((f) => (
        <Field
          key={f.key}
          label={f.label}
          required={f.required}
          hint={f.hint}
          className={f.full ? 'field-full' : ''}
        >
          {f.type === 'select' ? (
            <Select
              value={values[f.key] ?? ''}
              required={f.required}
              disabled={f.disabled}
              onChange={(e) => setField(f.key, e.target.value)}
            >
              <option value="">{f.placeholder || 'Select…'}</option>
              {(f.options || []).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </Select>
          ) : f.type === 'textarea' ? (
            <Textarea
              value={values[f.key] ?? ''}
              required={f.required}
              disabled={f.disabled}
              placeholder={f.placeholder}
              onChange={(e) => setField(f.key, e.target.value)}
            />
          ) : (
            <Input
              type={f.type || 'text'}
              value={values[f.key] ?? ''}
              required={f.required}
              disabled={f.disabled}
              placeholder={f.placeholder}
              step={f.step}
              min={f.min}
              onChange={(e) => setField(f.key, e.target.value)}
            />
          )}
        </Field>
      ))}
    </div>
  )
}

/** Initial form state from a schema (respects `default`). */
export function initialValues(fields) {
  return Object.fromEntries(fields.map((f) => [f.key, f.default ?? '']))
}

/** Form state prefilled from an existing row (for edit modals). */
export function editValues(fields, row) {
  return Object.fromEntries(
    fields.map((f) => {
      const v = row[f.key]
      if (v === undefined || v === null) return [f.key, '']
      // <select> options use string values
      return [f.key, f.type === 'select' ? String(v) : v]
    }),
  )
}

/**
 * Build an API payload from schema + values: number fields coerced via `num`,
 * empty optional fields dropped so the backend applies its defaults.
 *
 * With `clearNullable` (edit mode), empty fields marked `nullable: true` are
 * sent as explicit null so the backend clears them instead of ignoring them.
 */
export function buildPayload(fields, values, { clearNullable = false } = {}) {
  const out = {}
  for (const f of fields) {
    const raw = values[f.key]
    const empty = raw === '' || raw === undefined || raw === null
    if (empty) {
      if (f.required && f.type === 'number') out[f.key] = 0
      else if (clearNullable && f.nullable) out[f.key] = null
      continue // drop empty optionals
    }
    out[f.key] = f.type === 'number' ? num(raw) : raw
  }
  return out
}
