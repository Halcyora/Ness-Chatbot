import { useState, useRef } from 'react'

interface MessageInputProps {
  onSend: (message: string) => void
  isLoading: boolean
}

export default function MessageInput({
  onSend,
  isLoading,
}: MessageInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    if (input.trim()) {
      onSend(input.trim())
      setInput('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleTextareaChange = (
    e: React.ChangeEvent<HTMLTextAreaElement>
  ) => {
    const textarea = e.target
    setInput(textarea.value)
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  }

  return (
    <div className="flex gap-3">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={handleTextareaChange}
        onKeyDown={handleKeyDown}
        placeholder="Type your message... (Shift + Enter for new line)"
        disabled={isLoading}
        rows={1}
        className="flex-1 resize-none rounded-lg border border-gray-300 bg-white px-4 py-3 text-sm placeholder-gray-400 disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500 dark:disabled:bg-gray-600"
      />
      <button
        onClick={handleSend}
        disabled={isLoading || !input.trim()}
        className="rounded-lg bg-blue-500 px-4 py-3 font-medium text-white hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-gray-600"
        aria-label="Send message"
      >
        {isLoading ? '⏳' : '📤'}
      </button>
    </div>
  )
}
