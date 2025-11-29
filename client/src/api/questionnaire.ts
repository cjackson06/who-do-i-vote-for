import axios from 'axios';
import { Question } from '@/types/questionnaire';

const BASE_URL = 'http://localhost:8000';

// Description: Create a new session for the questionnaire
// Endpoint: POST /apps/political_profiler/users/user/sessions
// Response: { id: string }
export const createSession = async (): Promise<{ id: string }> => {
  try {
    const response = await axios.post(`${BASE_URL}/apps/political_profiler/users/user/sessions`);
    return response.data;
  } catch (error: any) {
    throw new Error(error?.response?.data?.message || error.message || 'Failed to create session');
  }
};

// Description: Get initial questionnaire question
// Endpoint: POST /run
// Request: { app_name: string, user_id: string, session_id: string, new_message: { parts: [{ text: string }], role: string } }
// Response: Array with nested structure containing parts[0].text
export const startQuestionnaire = async (): Promise<Question> => {
  try {
    const sessionId = localStorage.getItem('sessionId');
    if (!sessionId) {
      throw new Error('No session ID found. Please refresh the page.');
    }

    const response = await axios.post(`${BASE_URL}/run`, {
      app_name: 'political_profiler',
      user_id: 'user',
      session_id: sessionId,
      new_message: {
        parts: [
          {
            text: ''
          }
        ],
        role: 'user'
      }
    });
    
    // Extract the text from the nested response structure
    const responseData = response.data;
    const questionText = responseData[0]?.content?.parts?.[0]?.text || '';
    
    return {
      questionId: '1',
      question: questionText,
      questionNumber: 1,
      totalQuestions: 10
    };
  } catch (error: any) {
    throw new Error(error?.response?.data?.message || error.message || 'Failed to start questionnaire');
  }
};

// Description: Submit answer and get next question
// Endpoint: POST /run
// Request: { app_name: string, user_id: string, session_id: string, new_message: { parts: [{ text: string }], role: string } }
// Response: Array with nested structure containing parts[0].text
export const submitAnswer = async (
  data: { answer: string }
): Promise<Question & { isComplete: boolean }> => {
  try {
    const sessionId = localStorage.getItem('sessionId');
    if (!sessionId) {
      throw new Error('No session ID found. Please refresh the page.');
    }

    const response = await axios.post(`${BASE_URL}/run`, {
      app_name: 'political_profiler',
      user_id: 'user',
      session_id: sessionId,
      new_message: {
        parts: [
          {
            text: data.answer
          }
        ],
        role: 'user'
      }
    });
    
    // Extract the text from the nested response structure
    const responseData = response.data;
    const questionText = responseData[0]?.content?.parts?.[0]?.text || '';
    
    // Check if questionnaire is complete (you may need to adjust this logic based on your backend)
    const isComplete = questionText.toLowerCase().includes('complete') || 
                      questionText.toLowerCase().includes('finished') ||
                      !questionText;
    
    return {
      questionId: String(Date.now()),
      question: questionText,
      questionNumber: 1, // You may need to track this separately
      totalQuestions: 10,
      isComplete
    };
  } catch (error: any) {
    throw new Error(error?.response?.data?.message || error.message || 'Failed to submit answer');
  }
};
