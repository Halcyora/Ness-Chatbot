import type { QuickReply } from '../types'

interface QuickActionsProps {
  replies: QuickReply[]
  onSelect: (reply: QuickReply) => void
}

export default function QuickActions({
  replies,
  onSelect,
}: QuickActionsProps) {
  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex flex-wrap gap-2">
        {replies.map((reply) => (
          <button
            key={reply.id}
            onClick={() => onSelect(reply)}
            className="rounded-full border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-400 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          >
            {reply.icon && <span className="mr-2">{reply.icon}</span>}
            {reply.label}
          </button>
        ))}
      </div>
    </div>
  )
}
