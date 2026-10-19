import { useEffect, useRef, useState } from 'react'
import { chatbotApi } from '../api/chatbot'
import { useToast } from '../context/ToastContext'

/** Prior messages resent with each turn: 5 user + 5 assistant. */
export const MAX_HISTORY_MESSAGES = 10

/** UUID v4. `crypto.randomUUID` only exists in secure contexts (HTTPS / localhost),
 *  so fall back to `getRandomValues`, which works over plain HTTP as well. */
function newThreadId() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID()
  const b = crypto.getRandomValues(new Uint8Array(16))
  b[6] = (b[6] & 0x0f) | 0x40
  b[8] = (b[8] & 0x3f) | 0x80
  const h = [...b].map((x) => x.toString(16).padStart(2, '0')).join('')
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`
}

/** Flatten a token's content: plain string, or a list of text blocks. */
function textOf(content) {
  if (typeof content === 'string') return content
  if (Array.isArray(content)) return content.map((b) => (typeof b === 'string' ? b : b?.text || '')).join('')
  return ''
}

/** History text for a turn: its content plus the names of the files it carried. */
function historyText(m) {
  if (!m.attachments?.length) return m.content
  return `${m.content}\n[attached: ${m.attachments.map((a) => a.name).join(', ')}]`.trim()
}

/** Release the object URLs behind a transcript's image previews. */
function revokePreviews(list) {
  list.forEach((m) => m.attachments?.forEach((a) => a.previewUrl && URL.revokeObjectURL(a.previewUrl)))
}

/** Append streamed text to the trailing assistant message. */
function appendToLast(setMessages, chunk) {
  if (!chunk) return
  setMessages((list) => {
    const last = list[list.length - 1]
    return [...list.slice(0, -1), { ...last, content: last.content + chunk }]
  })
}

/**
 * Chat transcript state plus `send`, which streams the orchestrator's reply.
 *
 * Messages are `{role: 'user' | 'assistant', content, attachments?}`; a user
 * turn's `attachments` are `{name, content_type, size, previewUrl}`. `send(text, files)`
 * uploads the files first (`POST /chatbot/upload`) and streams the turn with their
 * ids; resent history is text only, with an `[attached: name]` marker. While a reply streams
 * the trailing assistant message grows token by token. A failed request drops
 * its empty assistant bubble and reports via toast; a stream-level `error`
 * event is exposed as `error` so the panel can show it inline.
 *
 * When the assistant wants to delete something the stream pauses with an
 * `interrupt` event; the requested actions are exposed as `pending` and
 * `decide('approve' | 'reject')` resumes the same reply.
 *
 * Every conversation has a client-generated `thread_id` so the backend can
 * resume a paused run. `reset` aborts any in-flight reply, clears the
 * transcript and starts a new thread.
 *
 * @returns {{messages, streaming, error, pending, send, decide, reset}}
 */
export function useChat() {
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState(null)
  const [pending, setPending] = useState(null)
  const abortRef = useRef(null)
  const threadRef = useRef(newThreadId())
  const toast = useToast()

  const messagesRef = useRef(messages)
  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  useEffect(
    () => () => {
      abortRef.current?.abort()
      revokePreviews(messagesRef.current)
    },
    [],
  )

  /** Stream one request into the trailing assistant bubble. */
  const run = async (body) => {
    const controller = new AbortController()
    abortRef.current = controller
    setError(null)
    setStreaming(true)
    try {
      const events = await chatbotApi.stream({ ...body, thread_id: threadRef.current }, { signal: controller.signal })
      for await (const ev of events) {
        if (ev.type === 'token') appendToLast(setMessages, textOf(ev.content))
        else if (ev.type === 'interrupt') setPending(ev.actions)
        else if (ev.type === 'error') setError(ev.message || 'The assistant failed to reply')
      }
    } catch (err) {
      if (err?.name === 'AbortError') return
      setMessages((list) => (list[list.length - 1]?.content ? list : list.slice(0, -1)))
      toast.error(err?.detail || err?.message || 'Chat request failed')
    } finally {
      setStreaming(false)
    }
  }

  /** Upload `files` (if any), then stream the turn with their ids. */
  const send = async (text, files = []) => {
    const message = text.trim()
    if ((!message && files.length === 0) || streaming || pending) return
    const history = messages
      .filter((m) => m.content || m.attachments?.length)
      .slice(-MAX_HISTORY_MESSAGES)
      .map((m) => ({ role: m.role, content: historyText(m) }))
    const attachments = files.map((file) => ({
      name: file.name,
      content_type: file.type,
      size: file.size,
      previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
    }))
    setMessages((list) => [...list, { role: 'user', content: message, attachments }, { role: 'assistant', content: '' }])
    let ids = []
    if (files.length > 0) {
      const controller = new AbortController()
      abortRef.current = controller
      setError(null)
      setStreaming(true)
      try {
        const uploaded = await Promise.all(files.map((file) => chatbotApi.upload(file, { signal: controller.signal })))
        ids = uploaded.map((u) => u.id)
      } catch (err) {
        setStreaming(false)
        if (err?.name === 'AbortError') return
        revokePreviews([{ attachments }])
        setMessages((list) => list.slice(0, -2))
        toast.error(err?.detail || err?.message || 'Attachment upload failed')
        return
      }
    }
    await run({ message, history, attachments: ids })
  }

  const decide = async (decision) => {
    if (!pending || streaming) return
    setPending(null)
    await run({ decision })
  }

  const reset = () => {
    abortRef.current?.abort()
    abortRef.current = null
    threadRef.current = newThreadId()
    revokePreviews(messages)
    setMessages([])
    setError(null)
    setPending(null)
    setStreaming(false)
  }

  return { messages, streaming, error, pending, send, decide, reset }
}
