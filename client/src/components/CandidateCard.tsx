import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CandidateMatch } from '@/types/questionnaire';
import { ChevronDown, ChevronUp, ExternalLink, CheckCircle, XCircle } from 'lucide-react';

interface CandidateCardProps {
  candidate: CandidateMatch;
  rank: number;
}

export function CandidateCard({ candidate, rank }: CandidateCardProps) {
  const [expanded, setExpanded] = useState(false);

  const getMatchColor = (percentage?: number, compatibility?: string) => {
    if (compatibility) {
      const level = compatibility.toLowerCase();
      if (level.includes('very high')) return 'from-green-500 to-emerald-600';
      if (level.includes('high')) return 'from-blue-500 to-cyan-600';
      if (level.includes('medium')) return 'from-yellow-500 to-orange-600';
      return 'from-red-500 to-pink-600';
    }
    if (percentage !== undefined) {
      if (percentage >= 80) return 'from-green-500 to-emerald-600';
      if (percentage >= 60) return 'from-blue-500 to-cyan-600';
      if (percentage >= 40) return 'from-yellow-500 to-orange-600';
      return 'from-red-500 to-pink-600';
    }
    return 'from-blue-500 to-purple-600';
  };

  const getRankBadge = (rank: number) => {
    const badges = ['🥇', '🥈', '🥉'];
    return badges[rank - 1] || `#${rank}`;
  };

  return (
    <Card className="border-0 bg-white/80 dark:bg-gray-800/80 backdrop-blur-lg shadow-lg hover:shadow-xl transition-all duration-300 animate-in fade-in slide-in-from-bottom-4">
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-start flex-1">
              {/* Info */}
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-2xl">{getRankBadge(rank)}</span>
                  <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {candidate.name}
                  </h3>
                </div>
                <Badge variant="secondary" className="mb-2">
                  {candidate.party}
                </Badge>
                <p className="text-gray-600 dark:text-gray-300 text-sm">
                  {candidate.summary}
                </p>
              </div>
            </div>

            {/* Match Display */}
            <div className="flex-shrink-0 ml-4">
              <div className={`w-24 h-24 rounded-full bg-gradient-to-br ${getMatchColor(candidate.matchPercentage, candidate.compatibility)} flex items-center justify-center shadow-lg`}>
                <div className="text-center px-2">
                  {candidate.compatibility ? (
                    <>
                      <div className="text-sm font-bold text-white leading-tight">
                        {candidate.compatibility}
                      </div>
                      <div className="text-xs text-white/90 mt-1">Match</div>
                    </>
                  ) : (
                    <>
                      <div className="text-3xl font-bold text-white">
                        {candidate.matchPercentage}%
                      </div>
                      <div className="text-xs text-white/90">Match</div>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Expand/Collapse Button */}
          <Button
            variant="ghost"
            onClick={() => setExpanded(!expanded)}
            className="w-full justify-between hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <span className="font-medium">
              {expanded ? 'Hide Details' : 'View Details'}
            </span>
            {expanded ? (
              <ChevronUp className="w-5 h-5" />
            ) : (
              <ChevronDown className="w-5 h-5" />
            )}
          </Button>

          {/* Expanded Content */}
          {expanded && (
            <div className="space-y-6 pt-4 border-t border-gray-200 dark:border-gray-700 animate-in fade-in slide-in-from-top-2 duration-300">
              {/* Areas of Alignment */}
              <div>
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-3 flex items-center">
                  <CheckCircle className="w-5 h-5 mr-2 text-green-600" />
                  Areas of Alignment
                </h4>
                <div className="space-y-3">
                  {candidate.alignment.map((item, index) => (
                    <div
                      key={index}
                      className="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800"
                    >
                      <div className="font-medium text-gray-900 dark:text-white mb-1">
                        {item.issue}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-300 space-y-1">
                        <div>
                          <span className="font-medium">Your view:</span> {item.userStance}
                        </div>
                        <div>
                          <span className="font-medium">Candidate:</span> {item.candidateStance}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Areas of Difference */}
              {candidate.differences.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-3 flex items-center">
                    <XCircle className="w-5 h-5 mr-2 text-red-600" />
                    Areas of Difference
                  </h4>
                  <div className="space-y-3">
                    {candidate.differences.map((item, index) => (
                      <div
                        key={index}
                        className="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
                      >
                        <div className="font-medium text-gray-900 dark:text-white mb-1">
                          {item.issue}
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-300 space-y-1">
                          <div>
                            <span className="font-medium">Your view:</span> {item.userStance}
                          </div>
                          <div>
                            <span className="font-medium">Candidate:</span> {item.candidateStance}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Key Policy Positions */}
              <div>
                <h4 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                  Key Policy Positions
                </h4>
                <ul className="space-y-2">
                  {candidate.keyPolicies.map((policy, index) => (
                    <li
                      key={index}
                      className="flex items-start text-gray-700 dark:text-gray-300"
                    >
                      <span className="mr-2 text-purple-600">•</span>
                      {policy}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Learn More Button */}
              <Button
                variant="outline"
                className="w-full"
                onClick={() => window.open(candidate.website, '_blank')}
              >
                Learn More
                <ExternalLink className="w-4 h-4 ml-2" />
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
