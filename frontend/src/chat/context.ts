import { createContext, useContext } from 'react'
import type { ChatMessage, FeedbackValue } from './types'

export interface ChatContextValue {
  messages: ChatMessage[]
  busy: boolean
  send: (text: string) => void
  retry: (assistantId: string) => void
  clear: () => void
  rate: (assistantId: string, value: FeedbackValue) => void
}

export const ChatContext = createContext<ChatContextValue | null>(null)

export function useChat(): ChatContextValue {
  const value = useContext(ChatContext)
  if (!value) throw new Error('useChat must be used inside ChatProvider')
  return value
}
