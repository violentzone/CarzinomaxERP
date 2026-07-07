/**
 * Form field primitives. `Field` wraps a labeled control; `Input`, `Select`,
 * `Textarea` are thin styled controls. Keep them controlled from the parent.
 */
export function Field({ label, hint, required, error, children, className = '' }) {
  return (
    <label className={`field ${className}`}>
      {label && (
        <span className="field-label">
          {label}
          {required && <span className="field-req">*</span>}
        </span>
      )}
      {children}
      {error ? (
        <span className="field-error">{error}</span>
      ) : hint ? (
        <span className="field-hint muted">{hint}</span>
      ) : null}
    </label>
  )
}

export function Input({ className = '', ...rest }) {
  return <input className={`control ${className}`} {...rest} />
}

export function Textarea({ className = '', ...rest }) {
  return <textarea className={`control ${className}`} rows={3} {...rest} />
}

export function Select({ className = '', children, ...rest }) {
  return (
    <select className={`control control-select ${className}`} {...rest}>
      {children}
    </select>
  )
}
