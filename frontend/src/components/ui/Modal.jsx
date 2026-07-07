import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { backdropVariants, modalVariants } from '../../lib/motion'

/**
 * Spring-animated modal dialog rendered in a portal. Closes on backdrop click
 * or Escape. Give it a `title`; `footer` renders a pinned action row.
 */
export default function Modal({ open, onClose, title, subtitle, children, footer, size = 'md' }) {
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
        <motion.div
          className="modal-backdrop"
          variants={backdropVariants}
          initial="hidden"
          animate="show"
          exit="hidden"
          onMouseDown={onClose}
        >
          <motion.div
            className={`modal glass modal-${size}`}
            variants={modalVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            onMouseDown={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
          >
            <div className="modal-head">
              <div>
                <h3>{title}</h3>
                {subtitle && <p className="muted">{subtitle}</p>}
              </div>
              <button className="icon-btn" onClick={onClose} aria-label="Close">
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">{children}</div>
            {footer && <div className="modal-foot">{footer}</div>}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
