import { titleize } from '../../lib/format'

/**
 * Status pill. Maps common ERP statuses / types to a tone; unknown values fall
 * back to a neutral tone. Pass `tone` to override.
 */
const STATUS_TONE = {
  // generic lifecycle
  paid: 'success',
  active: 'success',
  approved: 'success',
  completed: 'success',
  draft: 'neutral',
  pending: 'warning',
  rejected: 'danger',
  cancelled: 'danger',
  inactive: 'danger',
  // finance expense types
  paycheck: 'info',
  petty_cash: 'warning',
  investment: 'success',
  other: 'neutral',
  // leave types
  annual: 'info',
  sick: 'warning',
  unpaid: 'neutral',
  parental: 'success',
  // dev investment categories
  cloud: 'info',
  software_licenses: 'success',
  hardware: 'warning',
  consulting: 'danger',
  // download platforms
  github: 'neutral',
  dockerhub: 'info',
  npm: 'danger',
  pypi: 'warning',
}

export default function Badge({ children, status, tone, className = '', ...rest }) {
  const resolved = tone || (status ? STATUS_TONE[String(status).toLowerCase()] || 'neutral' : 'neutral')
  return (
    <span className={`badge badge-${resolved} ${className}`} {...rest}>
      <span className="badge-dot" />
      {children ?? titleize(status)}
    </span>
  )
}
