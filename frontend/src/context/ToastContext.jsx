/* eslint-disable react-refresh/only-export-components -- provider + useToast hook are intentionally colocated */
/**
 * Toast notifications. `useToast()` returns helpers (`success`, `error`, `info`)
 * used across forms to report API outcomes. Rendering lives in <ToastViewport>.
 */
import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, XCircle, Info, X } from 'lucide-react'
import { spring } from '../lib/motion'

const ToastContext = createContext(null)

const ICONS = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const remove = useCallback((id) => {
    setToasts((list) => list.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (type, message, ttl = 4200) => {
      const id = ++idRef.current
      setToasts((list) => [...list, { id, type, message }])
      if (ttl) setTimeout(() => remove(id), ttl)
      return id
    },
    [remove],
  )

  const api = {
    success: (m) => push('success', m),
    error: (m) => push('error', m),
    info: (m) => push('info', m),
    remove,
  }

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastViewport toasts={toasts} onClose={remove} />
    </ToastContext.Provider>
  )
}

function ToastViewport({ toasts, onClose }) {
  return (
    <div className="toast-viewport">
      <AnimatePresence>
        {toasts.map((t) => {
          const Icon = ICONS[t.type] || Info
          return (
            <motion.div
              key={t.id}
              className={`toast toast-${t.type} glass`}
              initial={{ opacity: 0, x: 40, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 40, scale: 0.9 }}
              transition={spring}
              layout
            >
              <Icon size={18} className="toast-icon" />
              <span className="toast-msg">{t.message}</span>
              <button className="toast-close" onClick={() => onClose(t.id)} aria-label="Dismiss">
                <X size={15} />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>')
  return ctx
}
