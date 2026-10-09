import { apiPostStream } from '../lib/api'

/** Yield one parsed object per line of a newline-delimited JSON body as chunks arrive. */
async function* readNdjson(response) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (line.trim()) yield JSON.parse(line)
    }
  }
  if (buffer.trim()) yield JSON.parse(buffer)
}

export const chatbotApi = {
  /**
   * Stream the orchestrator's reply. Send either `message` (a new turn) or
   * `decision` ('approve' | 'reject', answering a pending approval) together
   * with the conversation's `thread_id`. Resolves to an async iterator of
   * `{type:'token', content}`, `{type:'interrupt', actions:[{name, args, description}]}`,
   * `{type:'done'}` or `{type:'error', message}` events.
   */
  stream: async ({ message = '', history = [], thread_id, decision }, { signal } = {}) => {
    const res = await apiPostStream('/chatbot/chatbox', { message, history, thread_id, decision }, { signal })
    return readNdjson(res)
  },
}
