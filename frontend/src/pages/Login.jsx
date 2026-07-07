import { useState } from 'react'
import { useNavigate, useLocation, Navigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Mail, Lock, ArrowRight } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { Field, Input } from '../components/ui/Field'
import Button from '../components/ui/Button'

/** Sign-in screen with an animated gradient backdrop. */
export default function Login() {
  const { login, isAuthenticated } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const from = location.state?.from?.pathname || '/'

  if (isAuthenticated) return <Navigate to={from} replace />

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const me = await login(email.trim(), password)
      toast.success(`Welcome back, ${me.full_name || me.email}`)
      navigate(from, { replace: true })
    } catch (err) {
      toast.error(err?.detail || 'Sign in failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-screen">
      {['blob-1', 'blob-2', 'blob-3'].map((b, i) => (
        <motion.div
          key={b}
          className={`login-blob ${b}`}
          animate={{ x: [0, 24, -18, 0], y: [0, -20, 16, 0], scale: [1, 1.08, 0.96, 1] }}
          transition={{ duration: 14 + i * 3, repeat: Infinity, ease: 'easeInOut' }}
        />
      ))}

      <motion.div
        className="login-card"
        initial={{ opacity: 0, y: 20, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 24 }}
      >
        <div className="login-brand">
          <div className="brand-mark">C</div>
          <div>
            <div className="brand-name">Carzinomax</div>
            <div className="brand-sub">ERP</div>
          </div>
        </div>

        <div className="login-title">
          Welcome <span className="gradient-text">back</span>
        </div>
        <p className="login-sub">Sign in to your workspace to continue.</p>

        <form className="login-form" onSubmit={submit}>
          <Field label="Email">
            <div style={{ position: 'relative' }}>
              <Mail size={16} className="muted" style={iconStyle} />
              <Input
                type="email"
                required
                autoFocus
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ paddingLeft: 38 }}
              />
            </div>
          </Field>
          <Field label="Password">
            <div style={{ position: 'relative' }}>
              <Lock size={16} className="muted" style={iconStyle} />
              <Input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingLeft: 38 }}
              />
            </div>
          </Field>
          <Button type="submit" size="lg" loading={loading} className="grow">
            Sign in {!loading && <ArrowRight size={17} />}
          </Button>
        </form>

        <div className="login-hint">
          Use the seeded admin from your backend <code>.env</code> (<code>ADMIN_EMAIL</code> /
          <code> ADMIN_PASSWORD</code>).
        </div>
      </motion.div>
    </div>
  )
}

const iconStyle = {
  position: 'absolute',
  left: 12,
  top: '50%',
  transform: 'translateY(-50%)',
  pointerEvents: 'none',
}
