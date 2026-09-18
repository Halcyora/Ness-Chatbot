import React from 'react'
import ReactDOM from 'react-dom/client'
import ChatWidget from './ChatWidget'

export default ChatWidget

// Standalone entry point for embedding
if (typeof window !== 'undefined') {
  // Create a global function to initialize the widget
  (window as any).NessChatbotWidget = (config?: { apiUrl?: string; siteId?: string }) => {
    const container = document.getElementById('ness-chatbot-widget') || 
                      document.createElement('div')
    if (!container.id) {
      container.id = 'ness-chatbot-widget'
      document.body.appendChild(container)
    }

    const root = ReactDOM.createRoot(container)
    root.render(
      <React.StrictMode>
        <ChatWidget
          apiUrl={config?.apiUrl || 'http://localhost:8080'}
          siteId={config?.siteId || 'ness'}
        />
      </React.StrictMode>
    )
  }
}
