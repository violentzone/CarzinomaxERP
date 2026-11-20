import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { backdropVariants, drawerVariants } from '../../lib/motion'

/**
 * Right-hand slide-over drawer rendered in a portal, for forms too tall for a
 * modal. Closes on the X, Escape or a scrim click. Give it a `title`;
 * `footer` renders a pinned action row.
 */
export default function Drawer({ open, onClose, title, subtitle, children, footer }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  return createPortal(
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="drawer-scrim"
            variants={backdropVariants}
            initial="hidden"
            animate="show"
            exit="hidden"
            onClick={onClose}
          />
          <motion.aside
            className="drawer"
            variants={drawerVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            role="dialog"
            aria-modal="true"
            aria-label={title}
          >
            <div className="modal-head">
              <div>
                <h3>{title}</h3>
                {subtitle && <p className="muted">{subtitle}</p>}
              </div>
              <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
                <X size={18} />
              </button>
            </div>
            <div className="drawer-body">{children}</div>
            {footer && <div className="modal-foot">{footer}</div>}
          </motion.aside>
        </>
      )}
    </AnimatePresence>,
    document.body,
  )
}
