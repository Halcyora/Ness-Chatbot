import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import './App.css'
import type { ChatMessage, ChatResponse, ChatTrace, QuickReply } from './types'
import { useChat } from './hooks/useChat'

const SESSION_ID_KEY = 'kkr_chat_session_id'  // sessionStorage (per-tab)
const MESSAGES_KEY = 'kkr_chat_messages'       // sessionStorage (per-tab)

// Markdown components for rendering bot responses
const markdownComponents: Components = {
  p: ({ children }) => <p style={{ margin: '0.5em 0', lineHeight: 1.5 }}>{children}</p>,
  strong: ({ children }) => <strong style={{ fontWeight: 'bold' }}>{children}</strong>,
  em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#0066cc', textDecoration: 'underline' }}>
      {children}
    </a>
  ),
  ul: ({ children }) => (
    <ul style={{ margin: '0.5em 0', marginLeft: '1.5em', listStyle: 'disc' }}>
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol style={{ margin: '0.5em 0', marginLeft: '1.5em', listStyle: 'decimal' }}>
      {children}
    </ol>
  ),
  li: ({ children }) => <li style={{ margin: '0.25em 0' }}>{children}</li>,
  h1: ({ children }) => <h1 style={{ fontSize: '1.2em', fontWeight: 'bold', margin: '0.5em 0' }}>{children}</h1>,
  h2: ({ children }) => <h2 style={{ fontSize: '1.1em', fontWeight: 'bold', margin: '0.4em 0' }}>{children}</h2>,
  h3: ({ children }) => <h3 style={{ fontSize: '1em', fontWeight: 'bold', margin: '0.3em 0' }}>{children}</h3>,
  code: ({ children }) => (
    <code style={{ backgroundColor: 'rgba(0,0,0,0.1)', padding: '2px 4px', borderRadius: '3px', fontFamily: 'monospace', fontSize: '0.9em' }}>
      {children}
    </code>
  ),
  blockquote: ({ children }) => (
    <blockquote style={{ borderLeft: '3px solid #ccc', marginLeft: '0.5em', paddingLeft: '0.5em', fontStyle: 'italic', opacity: 0.8 }}>
      {children}
    </blockquote>
  ),
}

/**
 * Generate or retrieve a session ID for this tab.
 * 
 * Uses sessionStorage (not localStorage) so each NEW TAB/WINDOW gets a NEW session_id.
 * This allows multiple independent conversations in parallel.
 * Message history is also stored per-tab, so closing a tab loses that conversation.
 */
const getOrCreateSessionId = (): string => {
  let id = sessionStorage.getItem(SESSION_ID_KEY)
  if (!id) {
    id = (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`)
    sessionStorage.setItem(SESSION_ID_KEY, id)
  }
  return id
}

const loadSavedMessages = (): ChatMessage[] => {
  try {
    const raw = sessionStorage.getItem(MESSAGES_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as ChatMessage[]
    return parsed.map((m) => ({ ...m, timestamp: new Date(m.timestamp) }))
  } catch {
    return []
  }
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [darkMode, setDarkMode] = useState(false)
  const [input, setInput] = useState('')
  const [quickActions, setQuickActions] = useState<QuickReply[]>([])
  const sessionIdRef = useRef<string>(getOrCreateSessionId())
  const { sendMessage } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
    // Persist conversation for this tab (page refresh preserves it, but new tab loses it)
    if (messages.length > 0) {
      sessionStorage.setItem(MESSAGES_KEY, JSON.stringify(messages))
    }
  }, [messages])

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response: ChatResponse = await sendMessage(text, sessionIdRef.current)
      const botMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: response.reply,
        sender: 'bot',
        timestamp: new Date(),
        quickReplies: response.quick_replies,
        duration: response.duration_ms,
        trace: response.trace,
      }
      setMessages((prev) => [...prev, botMessage])
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: "Sorry, I couldn't process that. Please try again.",
        sender: 'bot',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
      console.error('Chat error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuickReply = (reply: QuickReply) => {
    const reply_with_route = reply as any
    
    // Handle different route types
    if (reply_with_route.route === 'tool') {
      // For tool calling, send a message that triggers the tool
      handleSendMessage(`Show ${reply_with_route.tool === 'get_open_positions' ? 'job openings' : 'latest news'}`)
    } else if (reply_with_route.route === 'rag') {
      // For RAG, send the configured query
      handleSendMessage(reply_with_route.query || reply.label)
    } else if (reply_with_route.route === 'canned') {
      // For canned responses, show the reply directly
      const botMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: reply_with_route.reply,
        sender: 'bot',
        timestamp: new Date(),
        trace: { handler: 'canned', llm_used: false },
      }
      setMessages((prev) => [...prev, botMessage])
    } else {
      // Fallback
      handleSendMessage(reply_with_route.query || reply.label)
    }
  }

  const handleClearCache = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('http://localhost:8080/session/clear-cache', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionIdRef.current }),
      })
      const data = await response.json()
      const botMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: `Cache cleared (${data.deleted_count ?? 0} entries removed). Conversation memory reset too. Future questions will get fresh answers.`,
        sender: 'bot',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, botMessage])
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I could not clear the cache. Please try again.',
        sender: 'bot',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
      console.error('Clear cache error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(input.trim())
    }
  }

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const textarea = e.target
    setInput(textarea.value)
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  }

  useEffect(() => {
    // Restore a persisted conversation (survives page refresh) or fetch a fresh greeting
    const initializeChat = async () => {
      const saved = loadSavedMessages()

      try {
        const response = await fetch('http://localhost:8080/session/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ site_id: 'kkr' }),
        })
        const data = await response.json()
        const quickActions = (data.quick_actions || []).map((action: any) => ({
          id: action.id,
          label: action.label,
          icon: action.icon,
          query: action.query, // Store the query for RAG buttons
          tool: action.tool, // Store the tool for tool-calling buttons
          route: action.route, // Store the route type
          reply: action.reply, // Store canned reply
        }))
        setQuickActions(quickActions)

        if (saved.length > 0) {
          setMessages(saved)
          return
        }

        const greeting: ChatMessage = {
          id: '0',
          text: data.welcome_message || 'Hi there! How can I help you today?',
          sender: 'bot',
          timestamp: new Date(),
        }
        setMessages([greeting])
      } catch (error) {
        console.error('Failed to load config:', error)

        if (saved.length > 0) {
          setMessages(saved)
        } else {
          // Fallback to hardcoded greeting
          const greeting: ChatMessage = {
            id: '0',
            text: 'Hi there! I\'m your KKR assistant. How can I help you today?',
            sender: 'bot',
            timestamp: new Date(),
          }
          setMessages([greeting])
        }
        setQuickActions([
          { id: 'about', label: 'About KKR', icon: 'ℹ️' },
          { id: 'investment', label: 'Investment Approach', icon: '💼' },
          { id: 'careers', label: 'Open Positions', icon: '🚀' },
          { id: 'insights', label: 'Latest Insights', icon: '📊' },
        ])
      }
    }
    
    initializeChat()
  }, [])

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    backgroundColor: darkMode ? '#1f2937' : '#ffffff',
    color: darkMode ? '#f3f4f6' : '#111827',
  }

  const headerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: `1px solid ${darkMode ? '#374151' : '#e5e7eb'}`,
    backgroundColor: darkMode ? '#111827' : '#f9fafb',
    padding: '16px 24px',
  }

  const titleStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  }

  const chatWindowStyle: React.CSSProperties = {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    padding: '16px',
  }

  const messageStyle = (sender: 'user' | 'bot'): React.CSSProperties => ({
    display: 'flex',
    justifyContent: sender === 'user' ? 'flex-end' : 'flex-start',
    marginBottom: '8px',
  })

  const bubbleStyle = (sender: 'user' | 'bot'): React.CSSProperties => ({
    maxWidth: '80%',
    padding: '12px 16px',
    borderRadius: '8px',
    backgroundColor: sender === 'user' ? '#3b82f6' : (darkMode ? '#374151' : '#e5e7eb'),
    color: sender === 'user' ? '#ffffff' : (darkMode ? '#f3f4f6' : '#111827'),
    wordWrap: 'break-word',
    boxShadow: sender === 'user' ? '0 4px 6px rgba(0,0,0,0.1)' : '0 1px 3px rgba(0,0,0,0.1)',
  })

  const traceStyle: React.CSSProperties = {
    maxWidth: '80%',
    marginTop: '4px',
    padding: '8px 12px',
    borderRadius: '6px',
    backgroundColor: darkMode ? '#0f172a' : '#f3f4f6',
    border: `1px dashed ${darkMode ? '#4b5563' : '#d1d5db'}`,
    color: darkMode ? '#9ca3af' : '#6b7280',
    fontSize: '11px',
    fontFamily: 'monospace',
    whiteSpace: 'pre-wrap',
  }

  // Build a short human-readable summary of the routing chain for a message trace
  const formatTrace = (trace?: ChatTrace): string | null => {
    if (!trace) return null
    const parts: string[] = []
    parts.push(`handler=${trace.handler ?? 'unknown'}`)
    if (trace.cached) parts.push('source=cache')
    if (trace.classification?.type) {
      parts.push(
        `intent=${trace.classification.type}${trace.classification.category ? `:${trace.classification.category}` : ''}`
      )
    }
    if (trace.rag) {
      parts.push(`chunks=${trace.rag.chunks_found ?? 0}`)
      if (trace.rag.scores && trace.rag.scores.length) parts.push(`scores=[${trace.rag.scores.join(', ')}]`)
    }
    if (trace.tool?.name) parts.push(`tool=${trace.tool.name}(${trace.tool.result_count ?? 0} results)`)
    parts.push(`llm=${trace.llm_used ? trace.llm_model || 'yes' : 'no'}`)
    if (trace.llm_used) parts.push(`grounded=${trace.grounded ?? 'n/a'}`)
    if (trace.grounding_fallback_used) parts.push('grounding_fallback=true')
    if (trace.error) parts.push(`error=${trace.error}`)
    if (trace.duration_ms !== undefined) parts.push(`took=${trace.duration_ms}ms`)
    return parts.join(' | ')
  }

  const inputContainerStyle: React.CSSProperties = {
    display: 'flex',
    gap: '12px',
    padding: '16px',
    borderTop: `1px solid ${darkMode ? '#374151' : '#e5e7eb'}`,
    backgroundColor: darkMode ? '#111827' : '#ffffff',
  }

  const textareaStyle: React.CSSProperties = {
    flex: 1,
    padding: '12px 16px',
    borderRadius: '8px',
    border: `1px solid ${darkMode ? '#4b5563' : '#d1d5db'}`,
    backgroundColor: darkMode ? '#1f2937' : '#ffffff',
    color: darkMode ? '#f3f4f6' : '#111827',
    fontFamily: 'inherit',
    fontSize: '14px',
    resize: 'none',
    maxHeight: '120px',
    minHeight: '40px',
  }

  const buttonStyle = (disabled?: boolean): React.CSSProperties => ({
    padding: '12px 16px',
    borderRadius: '8px',
    backgroundColor: disabled ? '#d1d5db' : '#3b82f6',
    color: disabled ? '#6b7280' : '#ffffff',
    border: 'none',
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: '500',
    fontSize: '14px',
  })

  const quickActionsStyle: React.CSSProperties = {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    padding: '16px',
    borderTop: `1px solid ${darkMode ? '#374151' : '#e5e7eb'}`,
    backgroundColor: darkMode ? '#111827' : '#ffffff',
  }

  const quickButtonStyle: React.CSSProperties = {
    padding: '8px 16px',
    borderRadius: '20px',
    border: `1px solid ${darkMode ? '#4b5563' : '#d1d5db'}`,
    backgroundColor: darkMode ? '#1f2937' : '#ffffff',
    color: darkMode ? '#f3f4f6' : '#111827',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s',
  }

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={headerStyle}>
        <div style={titleStyle}>
          <div style={{ fontSize: '24px' }}>🏢</div>
          <div>
            <h1 style={{ margin: 0, fontSize: '18px', fontWeight: '600' }}>
              KKR Assistant
            </h1>
            <p style={{ margin: 0, fontSize: '12px', opacity: 0.6, marginTop: '4px' }}>
              Your KKR Guide
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={handleClearCache}
            disabled={isLoading}
            title="Clear cached responses"
            style={{
              padding: '8px',
              borderRadius: '6px',
              backgroundColor: darkMode ? '#374151' : '#e5e7eb',
              border: 'none',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              fontSize: '18px',
              opacity: isLoading ? 0.5 : 1,
            }}
          >
            🗑️
          </button>
          <button
            onClick={() => setDarkMode(!darkMode)}
            style={{
              padding: '8px',
              borderRadius: '6px',
              backgroundColor: darkMode ? '#374151' : '#e5e7eb',
              border: 'none',
              cursor: 'pointer',
              fontSize: '18px',
            }}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div style={chatWindowStyle}>
        {messages.map((message) => (
          <div key={message.id} style={{ display: 'flex', flexDirection: 'column', alignItems: message.sender === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={messageStyle(message.sender)}>
              <div style={bubbleStyle(message.sender)}>
                {message.sender === 'user' ? (
                  <p style={{ margin: 0, lineHeight: 1.4 }}>{message.text}</p>
                ) : (
                  <div style={{ lineHeight: 1.5 }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                      {message.text}
                    </ReactMarkdown>
                  </div>
                )}
                {message.duration && (
                  <p style={{ margin: '8px 0 0 0', fontSize: '11px', opacity: 0.7 }}>
                    {(message.duration / 1000).toFixed(2)}s
                  </p>
                )}
              </div>
            </div>
            {message.sender === 'bot' && message.trace && (
              <div style={traceStyle}>{formatTrace(message.trace)}</div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      {quickActions.length > 0 && (
        <div style={quickActionsStyle}>
          {quickActions.map((reply) => (
            <button
              key={reply.id}
              onClick={() => handleQuickReply(reply)}
              style={quickButtonStyle}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)'
                e.currentTarget.style.transform = 'translateY(-1px)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'none'
                e.currentTarget.style.transform = 'translateY(0)'
              }}
            >
              {reply.label}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={inputContainerStyle}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleTextareaChange}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Shift + Enter for new line)"
          disabled={isLoading}
          rows={1}
          style={{ ...textareaStyle, opacity: isLoading ? 0.5 : 1 }}
        />
        <button
          onClick={() => handleSendMessage(input.trim())}
          disabled={isLoading || !input.trim()}
          style={buttonStyle(isLoading || !input.trim())}
        >
          {isLoading ? '⏳' : '📤'}
        </button>
      </div>
    </div>
  )
}

export default App
