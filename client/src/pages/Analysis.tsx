import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { analyzeCandidates } from '@/api/candidates';
import { useToast } from '@/hooks/useToast';
import { Loader2, Search, Database, TrendingUp } from 'lucide-react';

export function Analysis() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Analyzing your political views...');
  const hasAnalyzed = useRef(false);

  useEffect(() => {
    if (hasAnalyzed.current) return;
    hasAnalyzed.current = true;
    
    const analysisDataStr = sessionStorage.getItem('analysisData');
    if (!analysisDataStr) {
      toast({
        title: 'Error',
        description: 'No analysis data found. Please start over.',
        variant: 'destructive'
      });
      navigate('/candidates');
      return;
    }

    const analysisData = JSON.parse(analysisDataStr);
    const { politicalAlignment, candidates } = analysisData;

    const statusMessages = [
      { progress: 0, message: 'Analyzing your political views...' },
      { progress: 25, message: 'Researching candidate positions...' },
      { progress: 50, message: 'Comparing policy alignments...' },
      { progress: 75, message: 'Calculating compatibility scores...' },
    ];

    let currentIndex = 0;
    const interval = setInterval(() => {
      if (currentIndex < statusMessages.length) {
        setProgress(statusMessages[currentIndex].progress);
        setStatusMessage(statusMessages[currentIndex].message);
        currentIndex++;
      }
    }, 7000);

    const performAnalysis = async () => {
      try {
        const response = await analyzeCandidates(
          { politicalAlignment, candidates },
          () => {
            // Pre-response callback: set progress to 90%
            setProgress(90);
            setStatusMessage('Making recommendations...');
          }
        );
        
        // Store raw response for Results page to parse
        sessionStorage.setItem('analysisResponse', JSON.stringify(response));
        
        setProgress(100);
        setStatusMessage('Analysis complete!');
        
        await new Promise(resolve => setTimeout(resolve, 500));
        navigate('/results');
      } catch (error) {
        console.error('Error performing analysis:', error);
        toast({
          title: 'Error',
          description: error instanceof Error ? error.message : 'Failed to complete analysis',
          variant: 'destructive'
        });
        navigate('/candidates');
      }
    };

    performAnalysis();

    return () => clearInterval(interval);
  }, [navigate, toast]);

  const getIcon = () => {
    if (progress < 33) return Search;
    if (progress < 66) return Database;
    return TrendingUp;
  };

  const Icon = getIcon();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-purple-900 dark:to-gray-900 flex items-center justify-center">
      <div className="container mx-auto px-4">
        <div className="max-w-2xl mx-auto">
          <Card className="border-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur-lg shadow-2xl animate-in fade-in zoom-in duration-500">
            <CardContent className="p-12">
              <div className="text-center space-y-8">
                {/* Animated Icon */}
                <div className="flex justify-center">
                  <div className="relative">
                    <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center animate-pulse">
                      <Icon className="w-12 h-12 text-white" />
                    </div>
                    <div className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 animate-ping opacity-20"></div>
                  </div>
                </div>

                {/* Status Message */}
                <div className="space-y-4">
                  <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
                    Analyzing Your Matches
                  </h2>
                  <p className="text-lg text-gray-600 dark:text-gray-300 animate-pulse">
                    {statusMessage}
                  </p>
                </div>

                {/* Progress Bar */}
                <div className="space-y-2">
                  <Progress value={progress} className="h-3" />
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {progress}% Complete
                  </p>
                </div>

                {/* Loading Spinner */}
                <div className="flex justify-center">
                  <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
                </div>

                {/* Info Text */}
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  This usually takes 10-30 seconds. Please don't close this window.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
