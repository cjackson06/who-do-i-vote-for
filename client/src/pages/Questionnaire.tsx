import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/useToast';
import { startQuestionnaire, submitAnswer } from '@/api/questionnaire';
import { Question } from '@/types/questionnaire';
import { Send, Loader2 } from 'lucide-react';
import { ChatMessage } from '@/components/ChatMessage';

const INTRO_TEXT = "Hello! I'm here to have a conversation with you to understand your political views and the issues that are most important to you. My goal is to build a profile of your political stances, so I'll be asking open-ended questions across a range of topics. There are no right or wrong answers, and I'll maintain a neutral and respectful tone throughout. Feel free to elaborate as much as you like or let me know if you'd prefer to move on to another topic. To begin, what political issues or topics come to mind first when you think about what's important for the country or society today?";

type ChatEntry = {
  type: 'question' | 'answer';
  content: string;
  questionNumber?: number;
};

export function Questionnaire() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => 'session-' + Date.now());
  const [answers, setAnswers] = useState<Array<{ questionId: string; answer: string }>>([]);
  const [chatHistory, setChatHistory] = useState<ChatEntry[]>([
    { type: 'question', content: INTRO_TEXT }
  ]);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const loadInitialQuestion = useCallback(async () => {
    try {
      setLoading(true);
      const response = await startQuestionnaire(sessionId);
      setCurrentQuestion(response);
      setChatHistory(prev => [
        ...prev,
        { type: 'question', content: response.question, questionNumber: response.questionNumber }
      ]);
      console.log('Loaded initial question:', response);
    } catch (error: any) {
      console.error('Error loading question:', error);
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to load question',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadInitialQuestion();
  }, [loadInitialQuestion]);

  // Auto-scroll to bottom when chat history changes
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  const handleSubmit = async () => {
    if (!answer.trim()) {
      toast({
        title: 'Answer Required',
        description: 'Please provide an answer before continuing',
        variant: 'destructive'
      });
      return;
    }

    if (!currentQuestion) return;

    try {
      setLoading(true);

      // Add user's answer to chat history
      setChatHistory(prev => [...prev, {
        type: 'answer',
        content: answer
      }]);

      const newAnswers = [...answers, { questionId: currentQuestion.questionId, answer }];
      setAnswers(newAnswers);

      const response = await submitAnswer({
        questionId: currentQuestion.questionId,
        answer,
        sessionId
      });

      console.log('Submitted answer, received:', response);

      // Clear the input
      setAnswer('');

      if (response.isComplete) {
        // Store session data for next screen
        sessionStorage.setItem('questionnaireSession', sessionId);
        navigate('/candidates');
      } else {
        // Add next question to chat history
        setChatHistory(prev => [...prev, {
          type: 'question',
          content: response.question,
          questionNumber: response.questionNumber
        }]);
        setCurrentQuestion(response);
      }
    } catch (error: any) {
      console.error('Error submitting answer:', error);
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to submit answer',
        variant: 'destructive'
      });
    } finally {
        setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="fixed inset-0 bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-purple-900 dark:to-gray-900 flex flex-col">
      {/* Chat Container - Scrollable */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full">
          <div className="h-full flex flex-col">
            <div
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto py-6 px-4 space-y-1 container mx-auto max-w-4xl"
              style={{ scrollBehavior: 'smooth' }}
            >
              {chatHistory.length === 0 && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <Loader2 className="w-8 h-8 mx-auto mb-3 animate-spin text-blue-500" />
                    <p className="text-gray-500 dark:text-gray-400">Loading first question...</p>
                  </div>
                </div>
              )}

              {chatHistory.map((entry, index) => (
                <ChatMessage
                  key={index}
                  type={entry.type}
                  content={entry.content}
                  questionNumber={entry.questionNumber}
                  animate={index === chatHistory.length - 1}
                />
              ))}

              {loading && chatHistory.length > 0 && (
                <div className="flex justify-start gap-3 mb-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
                    <Loader2 className="w-5 h-5 text-white animate-spin" />
                  </div>
                  <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl px-4 py-3 shadow-md">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>
      </div>

      {/* Input Area - Fixed at bottom */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg py-4 px-4">
        <div className="container mx-auto max-w-4xl">
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <Textarea
                ref={textareaRef}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Type your answer... (Press Enter to send, Shift+Enter for new line)"
                className="min-h-[60px] max-h-[150px] text-base bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 focus:ring-2 focus:ring-blue-500 resize-none rounded-2xl"
                disabled={loading}
                rows={2}
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 px-3">
                Share your thoughts and perspectives. There are no right or wrong answers.
              </p>
            </div>
            <Button
              size="lg"
              onClick={handleSubmit}
              disabled={loading || !answer.trim()}
              className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-full shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 h-[60px] w-[60px] p-0"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
