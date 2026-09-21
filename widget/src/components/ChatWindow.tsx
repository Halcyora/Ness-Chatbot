import type { ChatMessage } from '../types'

interface ChatWindowProps {
  messages: ChatMessage[]
  messagesEndRef: React.RefObject<HTMLDivElement>
}

export default function ChatWindow({
  messages,
  messagesEndRef,
}: ChatWindowProps) {
  return (
    <div className="flex flex-col gap-4 px-4 py-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${
            message.sender === 'user' ? 'justify-end' : 'justify-start'
          }`}
        >
          <div
            className={`max-w-xs rounded-lg px-4 py-3 text-sm ${
              message.sender === 'user'
                ? 'bg-blue-500 text-white shadow-md'
                : 'bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white shadow-sm'
            }`}
          >
            <p className="break-words">{message.text}</p>
            {message.duration && (
              <p className="mt-1 text-xs opacity-70">
                {(message.duration / 1000).toFixed(2)}s
              </p>
            )}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  )
}
