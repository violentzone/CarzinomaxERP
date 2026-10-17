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
 * Messages are `{role: 'user' | 'assistant', content}`. While a reply streams
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

  useEffect(() => () => abortRef.current?.abort(), [])

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

  const send = async (text) => {
    const message = text.trim()
    if (!message || streaming || pending) return
    const history = messages.filter((m) => m.content).slice(-MAX_HISTORY_MESSAGES)
    setMessages((list) => [...list, { role: 'user', content: message }, { role: 'assistant', content: '' }])
    await run({ message, history })
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
    setMessages([])
    setError(null)
    setPending(null)
    setStreaming(false)
  }

  return { messages, streaming, error, pending, send, decide, reset }
}
