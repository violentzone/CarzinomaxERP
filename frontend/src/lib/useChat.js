import { useEffect, useRef, useState } from 'react'
import { chatbotApi } from '../api/chatbot'
import { useToast } from '../context/ToastContext'

/** Prior messages resent with each turn: 5 user + 5 assistant. */
export const MAX_HISTORY_MESSAGES = 10

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
 * `reset` aborts any in-flight reply and clears the transcript, starting a
 * new conversation.
 *
 * @returns {{messages, streaming, error, send, reset}}
 */
export function useChat() {
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)
  const toast = useToast()

  useEffect(() => () => abortRef.current?.abort(), [])

  const send = async (text) => {
    const message = text.trim()
    if (!message || streaming) return
    const history = messages.filter((m) => m.content).slice(-MAX_HISTORY_MESSAGES)
    const controller = new AbortController()
    abortRef.current = controller
    setError(null)
    setStreaming(true)
    setMessages((list) => [...list, { role: 'user', content: message }, { role: 'assistant', content: '' }])
    try {
      const events = await chatbotApi.stream({ message, history }, { signal: controller.signal })
      for await (const ev of events) {
        if (ev.type === 'token') appendToLast(setMessages, textOf(ev.content))
        else if (ev.type === 'error') setError(ev.message || 'The assistant failed to reply')
      }
    } catch (err) {
      if (err?.name === 'AbortError') return
      setMessages((list) => list.slice(0, -1))
      toast.error(err?.detail || err?.message || 'Chat request failed')
    } finally {
      setStreaming(false)
    }
  }

  const reset = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setMessages([])
    setError(null)
    setStreaming(false)
  }

  return { messages, streaming, error, send, reset }
}
