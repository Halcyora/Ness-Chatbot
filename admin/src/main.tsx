import React from 'react'
import ReactDOM from 'react-dom/client'
import AdminConsole from './AdminConsole'
import './index.css'

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <AdminConsole apiUrl="http://localhost:8080" siteId="ness" />
  </React.StrictMode>
)
