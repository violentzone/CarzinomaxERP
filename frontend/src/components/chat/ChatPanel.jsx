import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { FileText, MessageSquarePlus, Paperclip, Send, ShieldAlert, Sparkles, X } from 'lucide-react'
import { backdropVariants, drawerVariants } from '../../lib/motion'
import { useChat } from '../../lib/useChat'
import { fileSize } from '../../lib/format'
import { useToast } from '../../context/ToastContext'
import Button from '../ui/Button'
import Spinner from '../ui/Spinner'

/** Attachment limits; the backend (`POST /chatbot/upload`, `MAX_ATTACHMENTS`) enforces the same values. */
const ACCEPT = 'image/png,image/jpeg,image/webp,application/pdf'
const ACCEPTED_TYPES = new Set(ACCEPT.split(','))
const MAX_FILES = 5
const MAX_BYTES = 10 * 1024 * 1024

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
          {m.attachments?.length > 0 && (
            <div className="chat-msg-attachments">
              {m.attachments.map((a, j) =>
                a.previewUrl ? (
                  <img key={j} className="chat-msg-thumb" src={a.previewUrl} alt={a.name} />
                ) : (
                  <span key={j} className="chat-msg-file">
                    <FileText size={14} />
                    {a.name}
                  </span>
                ),
              )}
            </div>
          )}
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

/**
 * Input row: Enter sends, Shift+Enter inserts a newline. The paperclip or a
 * pasted image attaches files (PNG, JPEG, WebP, PDF; one image per message),
 * shown as chips above the row until sent; a message may be attachments only.
 */
function Composer({ onSend, busy }) {
  const [text, setText] = useState('')
  const [files, setFiles] = useState([])
  const inputRef = useRef(null)
  const fileRef = useRef(null)
  const toast = useToast()
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const addFiles = (incoming) => {
    const next = [...files]
    for (const file of incoming) {
      const duplicate = next.some((f) => f.file.name === file.name && f.file.size === file.size)
      if (duplicate) continue
      if (!ACCEPTED_TYPES.has(file.type)) toast.error(`${file.name}: only PNG, JPEG, WebP or PDF files can be attached`)
      else if (file.size > MAX_BYTES) toast.error(`${file.name} is larger than ${fileSize(MAX_BYTES)}`)
      else if (file.type.startsWith('image/') && next.some((f) => f.file.type.startsWith('image/'))) toast.error('Only one image per message')
      else if (next.length >= MAX_FILES) toast.error(`At most ${MAX_FILES} files per message`)
      else next.push({ file, previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null })
    }
    setFiles(next)
  }
  const removeFile = (index) => {
    const removed = files[index]
    if (removed?.previewUrl) URL.revokeObjectURL(removed.previewUrl)
    setFiles(files.filter((_, i) => i !== index))
  }
  const onPaste = (e) => {
    const pasted = [...e.clipboardData.items].filter((item) => item.kind === 'file').map((item) => item.getAsFile()).filter(Boolean)
    if (pasted.length === 0) return
    e.preventDefault()
    addFiles(pasted)
  }

  const submit = (e) => {
    e?.preventDefault()
    if (busy || (!text.trim() && files.length === 0)) return
    onSend(text, files.map((f) => f.file))
    // useChat creates its own preview URLs for the transcript bubble
    files.forEach((f) => f.previewUrl && URL.revokeObjectURL(f.previewUrl))
    setText('')
    setFiles([])
  }
  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) submit(e)
  }

  return (
    <form className="chat-foot" onSubmit={submit}>
      {files.length > 0 && (
        <div className="chat-attach-list">
          {files.map((f, i) => (
            <span key={`${f.file.name}-${f.file.size}`} className="chat-chip">
              {f.previewUrl ? (
                <img className="chat-chip-thumb" src={f.previewUrl} alt="" />
              ) : (
                <FileText size={14} className="chat-chip-icon" />
              )}
              <span className="chat-chip-name">{f.file.name}</span>
              <span className="chat-chip-size">{fileSize(f.file.size)}</span>
              <button
                type="button"
                className="icon-btn chat-chip-remove"
                onClick={() => removeFile(i)}
                aria-label={`Remove ${f.file.name}`}
              >
                <X size={14} />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="chat-foot-row">
        <button
          type="button"
          className="icon-btn"
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          aria-label="Attach a file"
          title="Attach an image or PDF"
        >
          <Paperclip size={18} />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          onChange={(e) => {
            addFiles([...e.target.files])
            e.target.value = ''
          }}
        />
        <textarea
          ref={inputRef}
          className="control chat-input"
          rows={1}
          placeholder={files.length > 0 ? 'Add a note or just send…' : 'Message the assistant…'}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
        />
        <Button type="submit" icon={Send} loading={busy} aria-label="Send" />
      </div>
    </form>
  )
}
