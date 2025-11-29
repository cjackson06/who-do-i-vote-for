import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/useToast';
import { analyzeCandidates, createMyPoliticianSession } from '@/api/candidates';
import { Users, X, Plus, ArrowRight, Loader2, MessageCircle } from 'lucide-react';

export function Candidates() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [candidateName, setCandidateName] = useState('');
  const [candidates, setCandidates] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [politicalAlignment, setPoliticalAlignment] = useState<string | null>(null);

  // Load political alignment and create my_politician session
  useEffect(() => {
    const alignment = localStorage.getItem('politicalAlignment');
    if (alignment) {
      setPoliticalAlignment(alignment);
      console.log('Loaded political alignment from localStorage');
    }

    // Create my_politician session if it doesn't exist
    const existingSessionId = sessionStorage.getItem('myPoliticianSessionId');
    if (!existingSessionId) {
      createMyPoliticianSession()
        .then((response) => {
          sessionStorage.setItem('myPoliticianSessionId', response.id);
          console.log('Created my_politician session:', response.id);
        })
        .catch((error) => {
          console.error('Error creating my_politician session:', error);
          toast({
            title: 'Session Error',
            description: 'Failed to initialize session. Please refresh the page.',
            variant: 'destructive'
          });
        });
    }
  }, [toast]);

  const handleAddCandidate = () => {
    if (!candidateName.trim()) {
      toast({
        title: 'Name Required',
        description: 'Please enter a candidate name',
        variant: 'destructive'
      });
      return;
    }

    if (candidates.includes(candidateName.trim())) {
      toast({
        title: 'Duplicate Candidate',
        description: 'This candidate has already been added',
        variant: 'destructive'
      });
      return;
    }

    setCandidates([...candidates, candidateName.trim()]);
    setCandidateName('');
    console.log('Added candidate:', candidateName.trim());
  };

  const handleRemoveCandidate = (candidate: string) => {
    setCandidates(candidates.filter(c => c !== candidate));
    console.log('Removed candidate:', candidate);
  };

  const handleAnalyze = async () => {
    if (candidates.length < 2) {
      toast({
        title: 'More Candidates Needed',
        description: 'Please add at least 2 candidates to compare',
        variant: 'destructive'
      });
      return;
    }

    if (!politicalAlignment) {
      toast({
        title: 'Missing Information',
        description: 'Please complete the questionnaire first',
        variant: 'destructive'
      });
      navigate('/questionnaire');
      return;
    }

    const myPoliticianSessionId = sessionStorage.getItem('myPoliticianSessionId');
    if (!myPoliticianSessionId) {
      toast({
        title: 'Session Error',
        description: 'Session not initialized. Please refresh the page.',
        variant: 'destructive'
      });
      return;
    }

    try {
      setLoading(true);
      console.log('Starting analysis with:', { politicalAlignment, candidates });
      
      // Store data for Analysis page to use
      sessionStorage.setItem('analysisData', JSON.stringify({
        politicalAlignment,
        candidates
      }));
      
      navigate('/analysis');
    } catch (error) {
      console.error('Error starting analysis:', error);
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to start analysis',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAddCandidate();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-purple-900 dark:to-gray-900">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12 animate-in fade-in slide-in-from-top-4 duration-500">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 mb-4 shadow-lg">
              <Users className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Who Are You Considering?
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-300">
              Add the candidates you're thinking about voting for
            </p>
          </div>

          {/* Political Alignment Summary */}
          {politicalAlignment && (
            <Card className="border-0 bg-gradient-to-br from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30 backdrop-blur-lg shadow-xl mb-6 animate-in fade-in slide-in-from-top-4 duration-500 delay-150">
              <CardContent className="p-6">
                <div className="flex gap-3">
                  <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
                    <MessageCircle className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-sm font-semibold text-blue-600 dark:text-blue-400 mb-2">
                      Your Political Profile
                    </h3>
                    <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
                      {politicalAlignment}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Input Card */}
          <Card className="border-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur-lg shadow-2xl mb-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <CardContent className="p-8">
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Candidate Name
                  </label>
                  <div className="flex space-x-2">
                    <Input
                      value={candidateName}
                      onChange={(e) => setCandidateName(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder="Enter candidate name..."
                      className="flex-1 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-purple-500"
                      disabled={loading}
                    />
                    <Button
                      onClick={handleAddCandidate}
                      disabled={loading}
                      className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white"
                    >
                      <Plus className="w-5 h-5" />
                    </Button>
                  </div>
                </div>

                {/* Candidates List */}
                {candidates.length > 0 && (
                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Selected Candidates ({candidates.length})
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {candidates.map((candidate, index) => (
                        <Badge
                          key={index}
                          variant="secondary"
                          className="px-4 py-2 text-sm bg-gradient-to-r from-blue-100 to-purple-100 dark:from-blue-900 dark:to-purple-900 text-gray-900 dark:text-white border-0 animate-in fade-in zoom-in duration-300"
                        >
                          {candidate}
                          <button
                            onClick={() => handleRemoveCandidate(candidate)}
                            className="ml-2 hover:text-red-600 transition-colors"
                            disabled={loading}
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {candidates.length < 2 && (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Add at least 2 candidates to continue
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Action Button */}
          <div className="flex justify-end animate-in fade-in slide-in-from-bottom-4 duration-500 delay-100">
            <Button
              size="lg"
              onClick={handleAnalyze}
              disabled={loading || candidates.length < 2}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 rounded-full shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Starting Analysis...
                </>
              ) : (
                <>
                  Analyze Matches
                  <ArrowRight className="w-5 h-5 ml-2" />
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
