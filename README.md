# Political Candidate Recommendation System

A full-stack application that uses AI agents to help users make informed voting decisions by analyzing political candidates against their personal beliefs and values.

## Features

- **AI-Powered Analysis**: Multi-agent system using Google ADK and Gemini models
- **Personalized Recommendations**: Match candidates based on your political beliefs
- **Interactive Questionnaire**: Structured approach to understanding your political stance
- **Candidate Research**: Automated research and analysis of political candidates
- **Compatibility Scoring**: Clear metrics showing alignment with your values

## Architecture

### Backend

- **Python 3.13+**
- **Google ADK**: Agentic AI framework for multi-agent orchestration

### Frontend

- **React 18.3** with **TypeScript**
- **Vite**: Fast build tool and dev server
- **shadcn/ui**: Beautiful, accessible component library
- **Tailwind CSS**: Utility-first styling
- **React Router**: Client-side routing

## Prerequisites

- **Docker** and **Docker Compose** (recommended)
- **Python 3.13+** (for local development)
- **Node.js 18+** and **npm** (for frontend development)
- **Google API Key** (for Gemini models)

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:

```bash
git clone https://github.com/cjackson06/who-do-i-vote-for.git
cd who-do-i-vote-for
```

2. Create a `.env` file in the root directory:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

3. Start the application:

```bash
docker-compose up
```

4. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

### Local Development

#### Backend Setup

1. Install Python dependencies using `uv`:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

2. Create `.env` file with required environment variables

3. Run the backend:

```bash
uv run adk api_server
```

#### Frontend Setup

1. Navigate to the client directory:

```bash
cd client
```

2. Install dependencies:

```bash
npm install
```

3. Start the development server:

```bash
npm run dev
```

4. Access the frontend at http://localhost:5173

## 📁 Project Structure

```
who-do-i-vote-for/
├── client/                    # Frontend React application
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/           # Page components
│   │   ├── api/             # API client functions
│   │   ├── hooks/           # Custom React hooks
│   │   └── types/           # TypeScript type definitions
│   └── Dockerfile           # Frontend container configuration
├── my_politician/            # AI Agent configurations
│   ├── root_agent.yaml      # Primary orchestrator agent
│   ├── candidate_analysis_workflow.yaml
│   ├── researcher_agent.yaml
│   ├── ideology_matcher_agent.yaml
│   └── recommender_agent.yaml
├── political_profiler/       # Additional agent configurations
├── docker-compose.yml       # Multi-container setup
├── Dockerfile               # Backend container configuration
├── pyproject.toml           # Python dependencies and config
└── README.md               # This file
```

## Contributing

We welcome contributions! Please see [CONTRIBUTIONS.md](CONTRIBUTIONS.md) for guidelines on how to contribute to this project.

## Development Tools

### Code Formatting & Linting

- Backend: `ruff` for formatting **and** linting (CI enforces
  `ruff check` + `ruff format --check`), `ty` for type checking
- Frontend: `eslint` for linting

```bash
# Format + lint backend
uv run ruff format .
uv run ruff check .

# Type check + tests
uv run ty check .
uv run pytest

# Lint frontend
cd client && npm run lint
```

### Commits

Conventional Commits via [commitizen](https://commitizen-tools.github.io/commitizen/):

```bash
uv run cz commit
```

## Troubleshooting

### Docker Issues

- Ensure Docker daemon is running
- Check port availability (3000, 8000)
- Try `docker-compose down -v` to reset volumes

### API Connection Issues

- Check backend logs: `docker-compose logs backend`
- Ensure Google API key has Gemini API access

### Frontend Build Errors

- Clear node_modules: `rm -rf client/node_modules && cd client && npm install`
- Check Node version: `node --version` (should be 18+)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or feedback, please open an issue on GitHub or contact the maintainers.

---

**Note**: This project is part of a Kaggle competition exploring agentic AI applications in civic engagement.
