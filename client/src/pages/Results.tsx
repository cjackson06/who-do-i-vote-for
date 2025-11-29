import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useToast } from '@/hooks/useToast';
import { CandidateMatch } from '@/types/questionnaire';
import { CandidateCard } from '@/components/CandidateCard';
import { Trophy, RotateCcw, Share2 } from 'lucide-react';

export function Results() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [results, setResults] = useState<CandidateMatch[]>([]);

  useEffect(() => {
    const resultsData = sessionStorage.getItem('analysisResults');
    if (!resultsData) {
      toast({
        title: 'No Results Found',
        description: 'Please complete the questionnaire first',
        variant: 'destructive'
      });
      navigate('/');
      return;
    }

    try {
      const parsed = JSON.parse(resultsData);
      setResults(parsed.results || []);
      console.log('Loaded results:', parsed.results);
    } catch (error) {
      console.error('Error parsing results:', error);
      toast({
        title: 'Error',
        description: 'Failed to load results',
        variant: 'destructive'
      });
      navigate('/');
    }
  }, [navigate, toast]);

  const handleStartOver = () => {
    sessionStorage.clear();
    navigate('/');
  };

  const handleShare = () => {
    toast({
      title: 'Share Feature',
      description: 'Sharing functionality would be implemented here',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-purple-900 dark:to-gray-900">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12 animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 mb-4 shadow-lg">
              <Trophy className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Your Candidate Matches
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-300 mb-6">
              Based on your political views, here are your best matches
            </p>

            {/* Action Buttons */}
            <div className="flex justify-center space-x-4">
              <Button
                variant="outline"
                onClick={handleShare}
                className="rounded-full"
              >
                <Share2 className="w-4 h-4 mr-2" />
                Share Results
              </Button>
              <Button
                variant="outline"
                onClick={handleStartOver}
                className="rounded-full"
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Start Over
              </Button>
            </div>
          </div>

          {/* Results List */}
          <div className="space-y-6">
            {results.map((candidate, index) => (
              <CandidateCard
                key={candidate.candidateId}
                candidate={candidate}
                rank={index + 1}
              />
            ))}
          </div>

          {/* Disclaimer */}
          <Card className="border-0 bg-white/60 dark:bg-gray-800/60 backdrop-blur-lg shadow-lg mt-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <CardContent className="p-6">
              <div className="text-center text-sm text-gray-600 dark:text-gray-300 space-y-2">
                <p className="font-semibold text-gray-900 dark:text-white">
                  Important Reminder
                </p>
                <p>
                  These results are based on publicly available information and your responses.
                  Always verify candidate positions independently and consider multiple sources when making your voting decision.
                </p>
                <p>
                  This tool is designed to be politically neutral and provide information only.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}