import React from 'react'
import ReactDOM from 'react-dom/client'
import ChatWidget from './ChatWidget'

// Dev-only entry point used by `npm run dev` to preview the widget live.
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ChatWidget apiUrl="http://localhost:8080" siteId="ness" />
  </React.StrictMode>
)
