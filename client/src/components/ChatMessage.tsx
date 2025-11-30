import { MessageCircle, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessageProps {
  type: 'question' | 'answer';
  content: string;
  questionNumber?: number;
  animate?: boolean;
  slideOut?: boolean;
}

export function ChatMessage({ type, content, questionNumber, animate = false, slideOut = false }: ChatMessageProps) {
  const isQuestion = type === 'question';

  return (
    <div
      className={`flex gap-3 mb-4 ${
        isQuestion ? 'justify-start' : 'justify-end'
      } ${animate ? 'animate-in fade-in slide-in-from-bottom-4 duration-500' : ''} ${
        slideOut ? 'animate-[slideOutLeft_0.5s_ease-in-out_forwards]' : ''
      }`}
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
        <div className={`text-sm leading-relaxed ${isQuestion ? 'text-gray-800 dark:text-gray-200' : 'text-white'} prose prose-sm max-w-none ${isQuestion ? 'dark:prose-invert' : 'prose-invert'}`}>
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
              ul: ({node, ...props}) => <ul className="list-disc list-inside mb-2" {...props} />,
              ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-2" {...props} />,
              li: ({node, ...props}) => <li className="mb-1" {...props} />,
              code: ({node, className, children, ...props}) => {
                const inline = !className;
                return inline ? (
                  <code className="bg-black bg-opacity-10 dark:bg-white dark:bg-opacity-10 px-1 py-0.5 rounded text-xs" {...props}>
                    {children}
                  </code>
                ) : (
                  <code className={`block bg-black bg-opacity-10 dark:bg-white dark:bg-opacity-10 p-2 rounded text-xs overflow-x-auto ${className}`} {...props}>
                    {children}
                  </code>
                );
              },
              strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
              em: ({node, ...props}) => <em className="italic" {...props} />,
              a: ({node, ...props}) => <a className="underline hover:no-underline" {...props} />,
              h1: ({node, ...props}) => <h1 className="text-lg font-bold mb-2" {...props} />,
              h2: ({node, ...props}) => <h2 className="text-base font-bold mb-2" {...props} />,
              h3: ({node, ...props}) => <h3 className="text-sm font-bold mb-1" {...props} />,
              blockquote: ({node, ...props}) => <blockquote className="border-l-2 border-current pl-2 italic" {...props} />,
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
      </div>

      {!isQuestion && (
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
}
