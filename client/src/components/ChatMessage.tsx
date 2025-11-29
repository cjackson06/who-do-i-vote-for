import { MessageCircle, User } from 'lucide-react';

interface ChatMessageProps {
  type: 'question' | 'answer';
  content: string;
  questionNumber?: number;
  animate?: boolean;
}

export function ChatMessage({ type, content, questionNumber, animate = false }: ChatMessageProps) {
  const isQuestion = type === 'question';

  return (
    <div
      className={`flex gap-3 mb-4 ${
        isQuestion ? 'justify-start' : 'justify-end'
      } ${animate ? 'animate-in fade-in slide-in-from-bottom-4 duration-500' : ''}`}
    >
      {isQuestion && (
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
          <MessageCircle className="w-5 h-5 text-white" />
        </div>
      )}

      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 shadow-md ${
          isQuestion
            ? 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'
            : 'bg-gradient-to-br from-blue-500 to-purple-600 text-white'
        }`}
      >
        {isQuestion && questionNumber && (
          <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 mb-1">
            Question {questionNumber}
          </div>
        )}
        <p className={`text-sm leading-relaxed ${isQuestion ? 'text-gray-800 dark:text-gray-200' : 'text-white'}`}>
          {content}
        </p>
      </div>

      {!isQuestion && (
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
}
