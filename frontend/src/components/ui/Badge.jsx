import { titleize } from '../../lib/format'

/**
 * Status pill. Maps common ERP statuses to a tone; unknown statuses fall back
 * to a neutral tone. Pass `tone` to override.
 */
const STATUS_TONE = {
  paid: 'success',
  received: 'success',
  active: 'success',
  approved: 'success',
  completed: 'success',
  delivered: 'success',
  posted: 'success',
  draft: 'neutral',
  pending: 'warning',
  applied: 'info',
  partially_paid: 'warning',
  in_transit: 'info',
  shipped: 'info',
  overdue: 'danger',
  rejected: 'danger',
  cancelled: 'danger',
  disposed: 'danger',
  inactive: 'danger',
}

export default function Badge({ children, status, tone, className = '' }) {
  const resolved = tone || (status ? STATUS_TONE[String(status).toLowerCase()] || 'neutral' : 'neutral')
  return (
    <span className={`badge badge-${resolved} ${className}`}>
      <span className="badge-dot" />
      {children ?? titleize(status)}
    </span>
  )
}
