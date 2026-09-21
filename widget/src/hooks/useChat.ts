import type { ChatResponse } from '../types'

const API_BASE_URL = 'http://localhost:8080'

export const useChat = () => {
  const sendMessage = async (message: string): Promise<ChatResponse> => {
    try {
      const response = await fetch(`${API_BASE_URL}/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          site_id: 'kkr',
          message,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data: ChatResponse = await response.json()
      return data
    } catch (error) {
      console.error('Error sending message:', error)
      throw error
    }
  }

  return {
    sendMessage,
  }
}
