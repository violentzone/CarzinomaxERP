/* eslint-disable react-refresh/only-export-components -- form helpers are colocated with the form component by design */
import { Field, Input, Select, Textarea } from './ui/Field'
import { num, toLocalInput, fromLocalInput } from '../lib/format'

/**
 * Render a controlled form from a field schema. Kept intentionally small — the
 * parent owns `values` and gets changes via `setField`.
 *
 * Field: { key, label, type, options?, required?, placeholder?, step?, min?, max?,
 *          hint?, full?(span both cols), default?, nullable?, disabled?, readOnly? }
 * type: 'text' | 'number' | 'email' | 'password' | 'date' | 'datetime-local'
 *       | 'select' | 'textarea' | 'checkbox'
 */
export function SchemaForm({ fields, values, setField }) {
  return (
    <div className="form-grid">
      {fields.map((f) => {
        if (f.type === 'checkbox') {
          return (
            <label key={f.key} className={`check-field ${f.full ? 'field-full' : ''}`}>
              <input
                type="checkbox"
                checked={!!values[f.key]}
                disabled={f.disabled}
                onChange={(e) => setField(f.key, e.target.checked)}
              />
              <span>
                <span className="field-label">{f.label}</span>
                {f.hint && <span className="field-hint muted">{f.hint}</span>}
              </span>
            </label>
          )
        }
        return (
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
                readOnly={f.readOnly}
                placeholder={f.placeholder}
                step={f.step}
                min={f.min}
                max={f.max}
                onChange={(e) => setField(f.key, e.target.value)}
              />
            )}
          </Field>
        )
      })}
    </div>
  )
}

/** Initial form state from a schema (respects `default`). */
export function initialValues(fields) {
  return Object.fromEntries(
    fields.map((f) => [f.key, f.default ?? (f.type === 'checkbox' ? false : '')]),
  )
}

/** Form state prefilled from an existing row (for edit modals). */
export function editValues(fields, row) {
  return Object.fromEntries(
    fields.map((f) => {
      const v = row[f.key]
      if (f.type === 'checkbox') return [f.key, !!v]
      if (v === undefined || v === null) return [f.key, '']
      if (f.type === 'datetime-local') return [f.key, toLocalInput(v)]
      // <select> options use string values
      return [f.key, f.type === 'select' ? String(v) : v]
    }),
  )
}

/**
 * Build an API payload from schema + values: number fields coerced via `num`,
 * datetime-local values converted to ISO, empty optional fields dropped so the
 * backend applies its defaults. Fields marked `omit` never reach the payload
 * (display-only / computed fields).
 *
 * With `clearNullable` (edit mode), empty fields marked `nullable: true` are
 * sent as explicit null so the backend clears them instead of ignoring them.
 * (Note: the current backend ignores nulls on update, so this is best-effort.)
 */
export function buildPayload(fields, values, { clearNullable = false } = {}) {
  const out = {}
  for (const f of fields) {
    if (f.omit) continue
    const raw = values[f.key]
    if (f.type === 'checkbox') {
      out[f.key] = !!raw
      continue
    }
    const empty = raw === '' || raw === undefined || raw === null
    if (empty) {
      if (f.required && f.type === 'number') out[f.key] = 0
      else if (clearNullable && f.nullable) out[f.key] = null
      continue // drop empty optionals
    }
    if (f.type === 'number') out[f.key] = num(raw)
    else if (f.type === 'datetime-local') out[f.key] = fromLocalInput(raw)
    else if (f.type === 'select' && f.numeric) out[f.key] = num(raw)
    else out[f.key] = raw
  }
  return out
}
