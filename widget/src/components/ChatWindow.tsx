import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import type { ChatMessage } from '../types'

interface ChatWindowProps {
  messages: ChatMessage[]
  messagesEndRef: React.RefObject<HTMLDivElement>
}

// Shared markdown renderers so bot replies render as proper rich text instead of raw ** ** / # syntax.
const markdownComponents: Components = {
  p: ({ children }) => <p className="mb-2 break-words leading-relaxed last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 underline hover:text-blue-700 dark:text-blue-300"
    >
      {children}
    </a>
  ),
  ul: ({ children }) => <ul className="mb-2 ml-4 list-disc space-y-1 last:mb-0">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal space-y-1 last:mb-0">{children}</ol>,
  li: ({ children }) => <li className="break-words">{children}</li>,
  h1: ({ children }) => <h1 className="mb-1 text-base font-bold">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-1 text-sm font-bold">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-1 text-sm font-semibold">{children}</h3>,
  code: ({ children }) => (
    <code className="rounded bg-black/10 px-1 py-0.5 font-mono text-xs dark:bg-white/10">
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre className="mb-2 overflow-x-auto rounded bg-black/10 p-2 text-xs last:mb-0 dark:bg-white/10">
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="mb-2 border-l-2 border-current/30 pl-2 italic opacity-90 last:mb-0">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="mb-2 overflow-x-auto last:mb-0">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-current/20 px-2 py-1 text-left font-semibold">{children}</th>
  ),
  td: ({ children }) => <td className="border border-current/20 px-2 py-1">{children}</td>,
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
            className={`rounded-lg px-4 py-3 text-sm ${
              message.sender === 'user'
                ? 'max-w-xs bg-blue-500 text-white shadow-md'
                : 'max-w-sm bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white shadow-sm'
            }`}
          >
            {message.sender === 'user' ? (
              <p className="break-words">{message.text}</p>
            ) : (
              <div className="break-words">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {message.text}
                </ReactMarkdown>
              </div>
            )}
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
