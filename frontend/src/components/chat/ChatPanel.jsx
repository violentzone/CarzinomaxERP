import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { MessageSquarePlus, Send, ShieldAlert, Sparkles, X } from 'lucide-react'
import { backdropVariants, drawerVariants } from '../../lib/motion'
import { useChat } from '../../lib/useChat'
import Button from '../ui/Button'
import Spinner from '../ui/Spinner'

/**
 * Right-hand slide-over chat drawer. The component stays mounted so the
 * transcript survives closing the drawer and route changes; `open` only
 * toggles the drawer DOM. Closes on the X, Escape or a scrim click.
 */
export default function ChatPanel({ open, onClose }) {
  const { messages, streaming, error, pending, send, decide, reset } = useChat()

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
            className="chat-scrim"
            variants={backdropVariants}
            initial="hidden"
            animate="show"
            exit="hidden"
            onClick={onClose}
          />
          <motion.aside
            className="chat-drawer"
            variants={drawerVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            role="dialog"
            aria-label="Assistant"
          >
            <div className="chat-head">
              <div className="chat-title">
                <Sparkles size={18} className="chat-title-icon" />
                <h3>Assistant</h3>
              </div>
              <div className="chat-actions">
                <button
                  className="icon-btn"
                  onClick={reset}
                  disabled={messages.length === 0}
                  aria-label="New conversation"
                  title="New conversation"
                >
                  <MessageSquarePlus size={18} />
                </button>
                <button className="icon-btn" onClick={onClose} aria-label="Close">
                  <X size={18} />
                </button>
              </div>
            </div>
            <MessageList messages={messages} streaming={streaming} error={error} />
            {pending && <ApprovalCard actions={pending} onDecide={decide} busy={streaming} />}
            <Composer onSend={send} busy={streaming || Boolean(pending)} />
          </motion.aside>
        </>
      )}
    </AnimatePresence>,
    document.body,
  )
}

/** Scrollable transcript; keeps the newest message in view. */
function MessageList({ messages, streaming, error }) {
  const endRef = useRef(null)
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, error])

  const lastIndex = messages.length - 1
  return (
    <div className="chat-messages">
      {messages.length === 0 && (
        <p className="chat-empty">Ask about people, payroll, expenses, products or dev projects, or tell me what to record.</p>
      )}
      {messages.map((m, i) => (
        <div key={i} className={`chat-msg ${m.role}`}>
          {m.content || (streaming && i === lastIndex ? <Spinner size={14} /> : null)}
        </div>
      ))}
      {error && <p className="chat-error">{error}</p>}
      <div ref={endRef} />
    </div>
  )
}

/** Format a tool argument for the approval card. */
function argText(value) {
  return typeof value === 'string' ? value : JSON.stringify(value)
}

/**
 * Shown while the assistant waits for permission to delete. Lists each
 * requested action with its arguments; Approve runs them, Reject cancels.
 */
function ApprovalCard({ actions, onDecide, busy }) {
  return (
    <div className="chat-approval" role="group" aria-label="Approval required">
      <div className="chat-approval-head">
        <ShieldAlert size={16} />
        <strong>Approval required</strong>
      </div>
      <ul className="chat-approval-list">
        {actions.map((a, i) => (
          <li key={i}>
            <code>{a.name}</code>
            <span className="chat-approval-args">
              {Object.entries(a.args || {})
                .map(([k, v]) => `${k}: ${argText(v)}`)
                .join(', ')}
            </span>
          </li>
        ))}
      </ul>
      <div className="chat-approval-actions">
        <Button variant="ghost" onClick={() => onDecide('reject')} disabled={busy}>
          Reject
        </Button>
        <Button variant="danger" onClick={() => onDecide('approve')} disabled={busy}>
          Approve
        </Button>
      </div>
    </div>
  )
}

/** Input row: Enter sends, Shift+Enter inserts a newline. */
function Composer({ onSend, busy }) {
  const [text, setText] = useState('')
  const inputRef = useRef(null)
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const submit = (e) => {
    e?.preventDefault()
    if (busy || !text.trim()) return
    onSend(text)
    setText('')
  }
  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) submit(e)
  }

  return (
    <form className="chat-foot" onSubmit={submit}>
      <textarea
        ref={inputRef}
        className="control chat-input"
        rows={1}
        placeholder="Message the assistant…"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
      />
      <Button type="submit" icon={Send} loading={busy} aria-label="Send" />
    </form>
  )
}
