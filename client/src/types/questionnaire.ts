export interface Question {
  questionId: string;
  question: string;
  questionNumber: number;
  totalQuestions: number;
  isComplete?: boolean;
}

export interface Answer {
  questionId: string;
  answer: string;
}

export interface CandidateAlignment {
  issue: string;
  userStance: string;
  candidateStance: string;
  agreement: boolean;
}

export interface CandidateMatch {
  candidateId: string;
  name: string;
  party: string;
  matchPercentage?: number;
  compatibility?: string;
  photo: string;
  summary: string;
  alignment: CandidateAlignment[];
  differences: CandidateAlignment[];
  keyPolicies: string[];
  website: string;
}
