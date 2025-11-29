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
export const analyzeCandidates = async (data: { 
  politicalAlignment: string; 
  candidates: string[] 
}) => {
  try {
    const myPoliticianSessionId = sessionStorage.getItem('myPoliticianSessionId');
    if (!myPoliticianSessionId) {
      throw new Error('No my_politician session ID found. Please refresh the page.');
    }
    
    const candidateArray = data.candidates.join(', ');
    
    const response = await axios.post(`${BASE_URL}/run`, {
      app_name: 'my_politician',
      user_id: 'user',
      session_id: myPoliticianSessionId,
      new_message: {
        parts: [{
          text: `${data.politicalAlignment}\n\n Who should I vote for? \n\n${candidateArray}`
        }],
        role: 'user'
      }
    });
    
    return response.data;
  } catch (error: any) {
    throw new Error(error?.response?.data?.message || error.message || 'Failed to analyze candidates');
  }
};

// Description: Get analysis results
// Endpoint: GET /api/candidates/results/:analysisId
// Request: {}
// Response: { results: Array<CandidateMatch> }
export const getAnalysisResults = (analysisId: string) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        results: [
          {
            candidateId: '1',
            name: 'Sarah Johnson',
            party: 'Progressive Party',
            matchPercentage: 87,
            photo: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Sarah',
            summary: 'Strong alignment on healthcare reform, environmental policy, and education funding. Your views on progressive taxation and social programs closely match her platform.',
            alignment: [
              {
                issue: 'Healthcare',
                userStance: 'Support universal healthcare',
                candidateStance: 'Advocates for Medicare for All',
                agreement: true
              },
              {
                issue: 'Climate Policy',
                userStance: 'Strong environmental regulations needed',
                candidateStance: 'Supports Green New Deal initiatives',
                agreement: true
              },
              {
                issue: 'Education',
                userStance: 'Public funding for higher education',
                candidateStance: 'Proposes tuition-free public colleges',
                agreement: true
              }
            ],
            differences: [
              {
                issue: 'Gun Control',
                userStance: 'Moderate restrictions',
                candidateStance: 'Comprehensive gun control legislation',
                agreement: false
              }
            ],
            keyPolicies: [
              'Universal healthcare coverage',
              'Aggressive climate action plan',
              'Free public college tuition',
              'Wealth tax on top earners',
              'Criminal justice reform'
            ],
            website: 'https://example.com/sarah-johnson'
          },
          {
            candidateId: '2',
            name: 'Michael Chen',
            party: 'Independent',
            matchPercentage: 72,
            photo: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Michael',
            summary: 'Moderate alignment on economic policy and government regulation. Shares your views on education but differs on healthcare approach and environmental priorities.',
            alignment: [
              {
                issue: 'Education',
                userStance: 'Public funding for higher education',
                candidateStance: 'Supports expanded Pell Grants',
                agreement: true
              },
              {
                issue: 'Business Regulation',
                userStance: 'Balanced approach to regulation',
                candidateStance: 'Moderate regulatory framework',
                agreement: true
              }
            ],
            differences: [
              {
                issue: 'Healthcare',
                userStance: 'Support universal healthcare',
                candidateStance: 'Public option with private insurance',
                agreement: false
              },
              {
                issue: 'Climate Policy',
                userStance: 'Strong environmental regulations needed',
                candidateStance: 'Market-based climate solutions',
                agreement: false
              }
            ],
            keyPolicies: [
              'Public-private healthcare partnership',
              'Incremental climate action',
              'Education investment',
              'Balanced budget approach',
              'Bipartisan governance'
            ],
            website: 'https://example.com/michael-chen'
          },
          {
            candidateId: '3',
            name: 'Robert Williams',
            party: 'Conservative Party',
            matchPercentage: 45,
            photo: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Robert',
            summary: 'Limited alignment on most major issues. Shares some views on government efficiency but differs significantly on healthcare, education funding, and environmental policy.',
            alignment: [
              {
                issue: 'Government Efficiency',
                userStance: 'Reduce bureaucratic waste',
                candidateStance: 'Streamline government operations',
                agreement: true
              }
            ],
            differences: [
              {
                issue: 'Healthcare',
                userStance: 'Support universal healthcare',
                candidateStance: 'Free market healthcare system',
                agreement: false
              },
              {
                issue: 'Education',
                userStance: 'Public funding for higher education',
                candidateStance: 'Private sector education solutions',
                agreement: false
              },
              {
                issue: 'Climate Policy',
                userStance: 'Strong environmental regulations needed',
                candidateStance: 'Minimal environmental regulation',
                agreement: false
              },
              {
                issue: 'Taxation',
                userStance: 'Progressive tax system',
                candidateStance: 'Flat tax rate',
                agreement: false
              }
            ],
            keyPolicies: [
              'Free market healthcare',
              'Lower taxes across the board',
              'Reduced government spending',
              'School choice and vouchers',
              'Energy independence'
            ],
            website: 'https://example.com/robert-williams'
          }
        ]
      });
    }, 2000);
  });
  // try {
  //   return await api.get(`/api/candidates/results/${analysisId}`);
  // } catch (error) {
  //   throw new Error(error?.response?.data?.message || error.message);
  // }
};
