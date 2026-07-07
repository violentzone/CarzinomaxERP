import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LogOut } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { navForRole, ROLE_LABELS } from '../../lib/roles'

/** Left navigation. Items are filtered by the current user's role. */
export default function Sidebar({ open, onNavigate }) {
  const { user, logout } = useAuth()
  const items = navForRole(user?.role)
  const initials = (user?.full_name || user?.email || '?')
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join('')

  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="brand">
        <div className="brand-mark">C</div>
        <div>
          <div className="brand-name">Carzinomax</div>
          <div className="brand-sub">ERP</div>
        </div>
      </div>

      <nav className="nav">
        <div className="nav-section-label">Workspace</div>
        {items.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.key}
              to={item.path}
              end={item.path === '/'}
              onClick={onNavigate}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-pill"
                      className="nav-active-pill"
                      transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                    />
                  )}
                  <span className="nav-icon">
                    <Icon size={19} />
                  </span>
                  <span>{item.label}</span>
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

      <div className="sidebar-foot">
        <div className="user-chip">
          <div className="avatar">{initials}</div>
          <div className="grow" style={{ minWidth: 0 }}>
            <div className="user-name" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.full_name || user?.email}
            </div>
            <div className="user-role">{ROLE_LABELS[user?.role] || user?.role}</div>
          </div>
          <button className="icon-btn" onClick={logout} aria-label="Sign out" title="Sign out">
            <LogOut size={17} />
          </button>
        </div>
      </div>
    </aside>
  )
}
