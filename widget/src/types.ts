export interface ChatMessage {
  id: string
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
  quickReplies?: QuickReply[]
  duration?: number
  trace?: ChatTrace
}

export interface ChatTrace {
  handler?: string
  cached?: boolean
  classification?: { type?: string; category?: string }
  llm_used?: boolean
  llm_model?: string
  grounded?: boolean
  grounding_fallback_used?: boolean
  rag?: {
    query?: string
    chunks_found?: number
    scores?: number[]
    sources?: string[]
  }
  tool?: {
    name?: string
    result_count?: number
  }
  duration_ms?: number
  error?: string
  reason?: string
}

export interface QuickReply {
  id: string
  label: string
  icon?: string
  route?: string
  tool?: string
  query?: string
}

export interface ChatResponse {
  reply: string
  quick_replies: QuickReply[]
  handler: string
  duration_ms: number
  trace?: ChatTrace
}

export interface ConversationHistory {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  messages: ChatMessage[]
}
