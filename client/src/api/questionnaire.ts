import api from './api';
import { Question } from '@/types/questionnaire';

// Description: Get initial questionnaire question
// Endpoint: POST /api/run
// Request: { appName: string, userId: string, sessionId: string, newMessage: string }
// Response: { questionId: string, question: string, questionNumber: number, totalQuestions: number }
export const startQuestionnaire = async (sessionId: string): Promise<Question> => {
  try {
    const response = await api.post('/api/run', {
      appName: 'Political_Profiler',
      userId: sessionId,
      sessionId: sessionId,
      newMessage: ''
    });
    return response.data;
  } catch (error: any) {
    throw new Error(error?.response?.data?.message || error.message);
  }
};

// Description: Submit answer and get next question
// Endpoint: POST /api/questionnaire/answer
// Request: { questionId: string, answer: string, sessionId: string }
// Response: { questionId: string, question: string, questionNumber: number, totalQuestions: number, isComplete: boolean }
export const submitAnswer = async (
  data: { questionId: string; answer: string; sessionId: string }
): Promise<Question & { isComplete: boolean }> => {
  try {
    const response = await api.post('/api/questionnaire/answer', data);
    return response.data;
  } catch (error: any) {
    throw new Error(error?.response?.data?.message || error.message);
  }
};
