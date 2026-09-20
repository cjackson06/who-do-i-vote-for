import axios from 'axios';

const BASE_URL = 'http://localhost:8000';

// Description: Create a new session for the my_politician app
// Endpoint: POST /apps/my_politician/users/user/sessions
// Response: { id: string }
export const createMyPoliticianSession = async (): Promise<{ id: string }> => {
  try {
    const response = await axios.post(`${BASE_URL}/apps/my_politician/users/user/sessions`);
    return response.data;
  } catch (error: any) {
    throw new Error(error?.response?.data?.message || error.message || 'Failed to create my_politician session');
  }
};

// Description: Analyze candidates against user responses
// Endpoint: POST /run
// Request: { app_name: string, user_id: string, session_id: string, new_message: { parts: [{ text: string }], role: string } }
// Response: Array with nested structure containing candidate analysis
export const analyzeCandidates = async (
  data: {
    politicalAlignment: string;
    candidates: string[]
  },
  onPreResponse?: () => void
) => {
  try {
    const myPoliticianSessionId = sessionStorage.getItem('myPoliticianSessionId');
    if (!myPoliticianSessionId) {
      throw new Error('No my_politician session ID found. Please refresh the page.');
    }

    const candidateArray = data.candidates.join(', ');

    const requestBody = {
      app_name: 'my_politician',
      user_id: 'user',
      session_id: myPoliticianSessionId,
      new_message: {
        parts: [{
          text: `${data.politicalAlignment}\n\n Who should I vote for? \n\n${candidateArray}`
        }],
        role: 'user'
      }
    };

    const response = await axios.post(`${BASE_URL}/run`, requestBody);

    // Check if this is a pre-response with functionCall
    const hasPreResponse = Array.isArray(response.data) &&
      response.data.some((item: any) =>
        item?.content?.parts?.some((part: any) => part?.functionCall)
      );

    if (hasPreResponse) {
      // Notify caller about pre-response
      if (onPreResponse) {
        onPreResponse();
      }
      setTimeout(() => {}, 2500);
      // Resend the POST with the same body to get the actual response
      const actualResponse = await axios.post(`${BASE_URL}/run`, requestBody);
      return actualResponse.data;
    }

    return response.data;
  } catch (error: any) {
    throw new Error(error?.response?.data?.message || error.message || 'Failed to analyze candidates');
  }
};
