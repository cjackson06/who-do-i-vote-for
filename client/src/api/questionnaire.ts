import api from './api';

// Description: Get initial questionnaire question
// Endpoint: GET /api/questionnaire/start
// Request: {}
// Response: { questionId: string, question: string, questionNumber: number, totalQuestions: number }
export const startQuestionnaire = () => {
  try {
     return api.get('/api/questionnaire/start');
  } catch (error) {
     throw new Error(error?.response?.data?.message || error.message);
  }
};

// Description: Submit answer and get next question
// Endpoint: POST /api/questionnaire/answer
// Request: { questionId: string, answer: string, sessionId: string }
// Response: { questionId: string, question: string, questionNumber: number, totalQuestions: number, isComplete: boolean }
export const submitAnswer = (data: { questionId: string; answer: string; sessionId: string }) => {
  try {
  return api.post('/api/questionnaire/answer', data);
   } catch (error) {
    throw new Error(error?.response?.data?.message || error.message);
   }
};