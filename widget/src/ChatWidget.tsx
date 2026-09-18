import React, { useState, useEffect, useRef } from 'react'

interface Message {
  id: string
  type: 'user' | 'bot'
  text: string
  timestamp: Date
}

interface QuickAction {
  label: string
  id: string
}

interface ChatWidgetProps {
  apiUrl?: string
  siteId?: string
  onMessage?: (message: string) => void
}

const ChatWidget: React.FC<ChatWidgetProps> = ({
  apiUrl = 'http://localhost:8080',
  siteId = 'ness',
  onMessage,
}) => {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [quickActions, setQuickActions] = useState<QuickAction[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Initialize session on mount
  useEffect(() => {
    initializeSession()
  }, [])

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const initializeSession = async () => {
    try {
      const response = await fetch(`${apiUrl}/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ site_id: siteId }),
      })

      const data = await response.json()
      
      // Add welcome message
      if (data.welcome_message) {
        setMessages([{
          id: '0',
          type: 'bot',
          text: data.welcome_message,
          timestamp: new Date(),
        }])
      }

      // Set quick actions
      if (data.quick_actions && Array.isArray(data.quick_actions)) {
        setQuickActions(data.quick_actions)
      }
    } catch (error) {
      console.error('Error initializing session:', error)
      setMessages([{
        id: '0',
        type: 'bot',
        text: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date(),
      }])
    }
  }

  const sendMessage = async (text: string) => {
    if (!text.trim()) return

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      text,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setInputValue('')
    setLoading(true)

    try {
      onMessage?.(text)

      const response = await fetch(`${apiUrl}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          site_id: siteId,
          message: text,
        }),
      })

      const data = await response.json()

      // Add bot response
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        text: data.reply || 'No response received.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, botMessage])

      // Update quick actions if provided
      if (data.quick_replies && Array.isArray(data.quick_replies)) {
        setQuickActions(data.quick_replies)
      }
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        text: 'Sorry, I encountered an error processing your message.',
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleQuickAction = (action: QuickAction) => {
    sendMessage(action.label)
  }

  return (
    <div className="ness-chatbot-widget">
      {/* Chat header */}
      <div className="chat-header">
        <h3>Ness Chatbot</h3>
        <button
          className="close-btn"
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? 'Close chat' : 'Open chat'}
        >
          {isOpen ? '−' : '+'}
        </button>
      </div>

      {/* Chat body */}
      {isOpen && (
        <div className="chat-body">
          {/* Messages container */}
          <div className="messages-container">
            {messages.map((msg) => (
              <div key={msg.id} className={`message message-${msg.type}`}>
                <div className="message-content">{msg.text}</div>
                <div className="message-time">
                  {msg.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </div>
              </div>
            ))}
            {loading && (
              <div className="message message-bot">
                <div className="message-content loading">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick actions */}
          {quickActions.length > 0 && !loading && (
            <div className="quick-actions">
              {quickActions.map((action) => (
                <button
                  key={action.id}
                  className="quick-action-btn"
                  onClick={() => handleQuickAction(action)}
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}

          {/* Input area */}
          <div className="input-area">
            <input
              type="text"
              className="message-input"
              placeholder="Type your message..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !loading) {
                  sendMessage(inputValue)
                }
              }}
              disabled={loading}
            />
            <button
              className="send-btn"
              onClick={() => sendMessage(inputValue)}
              disabled={loading || !inputValue.trim()}
              aria-label="Send message"
            >
              ➤
            </button>
          </div>
        </div>
      )}

      {/* Styles */}
      <style>{`
        .ness-chatbot-widget {
          position: fixed;
          bottom: 20px;
          right: 20px;
          width: 380px;
          max-width: 100%;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
          background: white;
          border-radius: 8px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          z-index: 9999;
          display: flex;
          flex-direction: column;
          max-height: 600px;
        }

        .chat-header {
          background: #1e40af;
          color: white;
          padding: 16px;
          border-radius: 8px 8px 0 0;
          display: flex;
          justify-content: space-between;
          align-items: center;
          cursor: pointer;
        }

        .chat-header h3 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
        }

        .close-btn {
          background: none;
          border: none;
          color: white;
          font-size: 24px;
          cursor: pointer;
          padding: 0;
          width: 32px;
          height: 32px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 4px;
          transition: background 0.2s;
        }

        .close-btn:hover {
          background: rgba(255, 255, 255, 0.2);
        }

        .chat-body {
          display: flex;
          flex-direction: column;
          flex: 1;
          min-height: 0;
        }

        .messages-container {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .message {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .message-user {
          align-items: flex-end;
        }

        .message-user .message-content {
          background: #1e40af;
          color: white;
          border-radius: 12px 12px 4px 12px;
        }

        .message-bot {
          align-items: flex-start;
        }

        .message-bot .message-content {
          background: #f3f4f6;
          color: #1f2937;
          border-radius: 12px 12px 12px 4px;
        }

        .message-content {
          padding: 10px 14px;
          max-width: 85%;
          word-wrap: break-word;
          line-height: 1.4;
          font-size: 14px;
        }

        .message-time {
          font-size: 12px;
          color: #9ca3af;
          padding: 0 4px;
        }

        .message-content.loading {
          display: flex;
          gap: 4px;
          padding: 12px 14px;
        }

        .message-content.loading span {
          width: 6px;
          height: 6px;
          background: #9ca3af;
          border-radius: 50%;
          animation: pulse 1.4s infinite;
        }

        .message-content.loading span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .message-content.loading span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 1; }
        }

        .quick-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          padding: 12px 16px;
          border-top: 1px solid #e5e7eb;
        }

        .quick-action-btn {
          background: #f3f4f6;
          border: 1px solid #d1d5db;
          border-radius: 20px;
          padding: 8px 12px;
          font-size: 12px;
          color: #1f2937;
          cursor: pointer;
          transition: all 0.2s;
          flex-shrink: 0;
        }

        .quick-action-btn:hover {
          background: #e5e7eb;
          border-color: #9ca3af;
        }

        .quick-action-btn:active {
          transform: scale(0.95);
        }

        .input-area {
          display: flex;
          gap: 8px;
          padding: 12px;
          border-top: 1px solid #e5e7eb;
          background: #fafafa;
          border-radius: 0 0 8px 8px;
        }

        .message-input {
          flex: 1;
          border: 1px solid #d1d5db;
          border-radius: 20px;
          padding: 8px 14px;
          font-size: 14px;
          outline: none;
          transition: border-color 0.2s;
        }

        .message-input:focus {
          border-color: #1e40af;
        }

        .message-input:disabled {
          background: #f3f4f6;
          cursor: not-allowed;
        }

        .send-btn {
          background: #1e40af;
          color: white;
          border: none;
          border-radius: 50%;
          width: 36px;
          height: 36px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s;
          font-size: 16px;
        }

        .send-btn:hover:not(:disabled) {
          background: #1e3a8a;
          transform: scale(1.05);
        }

        .send-btn:disabled {
          background: #9ca3af;
          cursor: not-allowed;
        }

        @media (max-width: 480px) {
          .ness-chatbot-widget {
            width: calc(100% - 40px);
            height: calc(100vh - 80px);
            max-height: none;
            bottom: 10px;
            right: 10px;
            left: 10px;
            border-radius: 4px;
          }
        }
      `}</style>
    </div>
  )
}

export default ChatWidget
