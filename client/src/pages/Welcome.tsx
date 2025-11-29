import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Vote, CheckCircle, Users, TrendingUp } from 'lucide-react';

export function Welcome() {
  const navigate = useNavigate();

  const features = [
    {
      icon: Vote,
      title: 'Personalized Matching',
      description: 'Answer questions about your political views to find candidates that align with your values'
    },
    {
      icon: CheckCircle,
      title: 'Data-Driven Results',
      description: 'Get objective analysis based on actual candidate positions and voting records'
    },
    {
      icon: Users,
      title: 'Compare Candidates',
      description: 'See side-by-side comparisons of where you agree and disagree with each candidate'
    },
    {
      icon: TrendingUp,
      title: 'Make Informed Decisions',
      description: 'Access detailed policy positions and sources to verify information'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-purple-900 dark:to-gray-900">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto">
          {/* Hero Section */}
          <div className="text-center mb-16 animate-in fade-in slide-in-from-bottom-4 duration-1000">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 mb-6 shadow-lg">
              <Vote className="w-10 h-10 text-white" />
            </div>
            <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              Find Your Ideal Candidate
            </h1>
            <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
              Discover which political candidates best match your views through our intelligent questionnaire
            </p>
            <Button
              size="lg"
              onClick={() => navigate('/questionnaire')}
              className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white px-8 py-6 text-lg rounded-full shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105"
            >
              Get Started
            </Button>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-2 gap-6 mb-12">
            {features.map((feature, index) => (
              <Card
                key={index}
                className="border-0 bg-white/60 dark:bg-gray-800/60 backdrop-blur-lg shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 animate-in fade-in slide-in-from-bottom-4"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <CardContent className="p-6">
                  <div className="flex items-start space-x-4">
                    <div className="flex-shrink-0">
                      <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                        <feature.icon className="w-6 h-6 text-white" />
                      </div>
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">
                        {feature.title}
                      </h3>
                      <p className="text-gray-600 dark:text-gray-300">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Disclaimer */}
          <Card className="border-0 bg-white/60 dark:bg-gray-800/60 backdrop-blur-lg shadow-lg">
            <CardContent className="p-6">
              <div className="text-center text-sm text-gray-600 dark:text-gray-300 space-y-2">
                <p className="font-semibold text-gray-900 dark:text-white">Important Information</p>
                <p>
                  This tool provides information based on publicly available data and should be one of many resources in your voting decision.
                </p>
                <p>
                  Your answers are used only to generate your matches and are not stored or shared.
                </p>
                <p>
                  Our matching algorithm is designed to be politically neutral and bases recommendations solely on policy alignment.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}