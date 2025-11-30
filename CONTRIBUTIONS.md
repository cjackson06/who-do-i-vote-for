# Contributing to Kaggle Agentic AI

Thank you for your interest in contributing to the Political Candidate Recommendation System! We welcome contributions from the community and are excited to have you join us in building a tool that helps voters make informed decisions.

## Project Goals

This project aims to:

- Help voters understand candidate positions through AI-powered analysis
- Provide unbiased, fact-based recommendations
- Create an accessible and user-friendly voting decision tool
- Explore innovative applications of agentic AI in civic engagement

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of background, identity, or experience level.

### Expected Behavior

- Be respectful and considerate in communication
- Provide constructive feedback
- Focus on what is best for the project and community
- Show empathy towards other community members
- Accept constructive criticism gracefully

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Trolling, insulting, or derogatory remarks
- Publishing others' private information
- Any conduct that would be inappropriate in a professional setting

## How to Contribute

### Reporting Bugs

Before submitting a bug report:

1. Check the existing [GitHub issues](https://github.com/cjackson06/kaggle-agentic-ai/issues) to avoid duplicates
2. Update to the latest version to see if the issue persists
3. Collect relevant information (logs, screenshots, reproduction steps)

When submitting a bug report, include:

- Clear, descriptive title
- Detailed steps to reproduce the issue
- Expected vs. actual behavior
- Environment details (OS, Python version, Node version, etc.)
- Screenshots or error logs if applicable
- Minimal code example demonstrating the issue

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- Use a clear and descriptive title
- Provide detailed description of the proposed functionality
- Explain why this enhancement would be useful
- Include mockups or examples if applicable
- Consider the impact on existing functionality

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Test your changes** thoroughly
4. **Update documentation** if needed
5. **Submit a pull request** with a clear description

## Development Setup

### Prerequisites

- Python 3.13+
- Node.js 18+
- Docker and Docker Compose
- Git
- Code editor (VS Code recommended)

### Initial Setup

1. Fork and clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/kaggle-agentic-ai.git
cd kaggle-agentic-ai
```

2. Set up the backend:

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies
uv sync --group dev
```

3. Set up the frontend:

```bash
cd client
npm install
```

4. Create `.env` file:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```

5. Run the application:

```bash
# Using Docker
docker-compose up

# Or run separately
# Terminal 1 - Backend
uv run python -m app.main

# Terminal 2 - Frontend
cd client && npm run dev
```

## Coding Standards

### Python (Backend)

#### Style Guide

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [Flake8](https://flake8.pycqa.org/) for linting
- Maximum line length: 88 characters (Black default)

#### Formatting

```bash
# Format code
uv run black .

# Check linting
uv run flake8 .
```

#### Best Practices

- Write descriptive function and variable names
- Add type hints to function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Use meaningful commit messages

Example:

```python
from typing import List, Dict, Optional

def analyze_candidate_compatibility(
    user_beliefs: Dict[str, str],
    candidate_positions: Dict[str, str]
) -> Dict[str, float]:
    """
    Analyze compatibility between user beliefs and candidate positions.

    Args:
        user_beliefs: Dictionary of user's political beliefs
        candidate_positions: Dictionary of candidate's positions

    Returns:
        Dictionary with compatibility scores by topic
    """
    # Implementation here
    pass
```

### TypeScript/React (Frontend)

#### Style Guide

- Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- Use ESLint for linting
- Use Prettier for formatting
- Prefer functional components with hooks

#### Formatting

```bash
cd client
npm run lint
npm run lint:fix  # Auto-fix issues
```

#### Best Practices

- Use TypeScript for type safety
- Prefer composition over inheritance
- Keep components small and focused
- Use meaningful prop names
- Write self-documenting code

Example:

```typescript
interface CandidateCardProps {
  name: string;
  party: string;
  compatibility: number;
  onSelect: (candidateId: string) => void;
}

export function CandidateCard({
  name,
  party,
  compatibility,
  onSelect,
}: CandidateCardProps) {
  return <div className="candidate-card">{/* Component implementation */}</div>;
}
```

### AI Agent Configuration (YAML)

#### Guidelines

- Use clear, descriptive agent names
- Write detailed instructions for agent behavior
- Document expected inputs and outputs
- Keep configurations version controlled
- Test agent interactions thoroughly

Example:

```yaml
name: Researcher_Agent
agent_class: LlmAgent
model: gemini-2.5-flash
instruction: |
  You are responsible for researching candidate information.
  Your task is to gather factual data about candidates including:
  - Policy positions
  - Voting records
  - Public statements
  Always cite sources and verify information accuracy.
```

## Git Workflow

### Branch Naming Convention

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Urgent production fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test additions/updates

Examples:

- `feature/candidate-comparison-view`
- `bugfix/fix-recommendation-scoring`
- `docs/update-api-documentation`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:

```bash
feat(frontend): add candidate comparison view
fix(backend): resolve API timeout issue
docs(readme): update installation instructions
test(agents): add unit tests for ideology matcher
```

### Pull Request Process

1. **Update your branch** with the latest `main`:

```bash
git checkout main
git pull origin main
git checkout your-branch
git rebase main
```

2. **Ensure all tests pass**:

```bash
# Backend tests
uv run pytest

# Frontend tests
cd client && npm run test
```

3. **Create pull request** with:

   - Clear, descriptive title
   - Detailed description of changes
   - Link to related issues
   - Screenshots (for UI changes)
   - Test coverage information

4. **Address review feedback**:

   - Respond to all comments
   - Make requested changes
   - Re-request review after updates

5. **Squash and merge** once approved

## Testing Guidelines

### Backend Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_agents.py

# Run with coverage
uv run pytest --cov=. --cov-report=html
```

#### Test Structure

- Place tests in `tests/` directory
- Mirror source code structure
- Use descriptive test names
- Include both positive and negative test cases

Example:

```python
import pytest
from app.agents import IdeologyMatcher

def test_ideology_matcher_high_compatibility():
    """Test that ideology matcher correctly identifies high compatibility."""
    matcher = IdeologyMatcher()
    result = matcher.analyze(
        user_beliefs={"economy": "progressive"},
        candidate_positions={"economy": "progressive"}
    )
    assert result.compatibility > 0.8

def test_ideology_matcher_low_compatibility():
    """Test that ideology matcher correctly identifies low compatibility."""
    matcher = IdeologyMatcher()
    result = matcher.analyze(
        user_beliefs={"economy": "progressive"},
        candidate_positions={"economy": "conservative"}
    )
    assert result.compatibility < 0.3
```

### Frontend Testing

```bash
cd client

# Run tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

#### Test Structure

- Use React Testing Library
- Test user interactions, not implementation
- Write accessible tests
- Mock API calls appropriately

Example:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { CandidateCard } from "./CandidateCard";

describe("CandidateCard", () => {
  it("displays candidate information correctly", () => {
    render(
      <CandidateCard
        name="John Doe"
        party="Independent"
        compatibility={0.85}
        onSelect={jest.fn()}
      />
    );

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("Independent")).toBeInTheDocument();
  });

  it("calls onSelect when clicked", () => {
    const handleSelect = jest.fn();
    render(
      <CandidateCard
        name="John Doe"
        party="Independent"
        compatibility={0.85}
        onSelect={handleSelect}
      />
    );

    fireEvent.click(screen.getByRole("button"));
    expect(handleSelect).toHaveBeenCalledWith("john-doe");
  });
});
```

## Documentation

### Code Documentation

- Add docstrings to all Python functions/classes
- Use JSDoc comments for TypeScript functions
- Keep comments up-to-date with code changes
- Explain "why" not "what" in comments

### README Updates

When adding features, update:

- Features section
- Installation instructions (if needed)
- Configuration options (if needed)
- Examples and usage

### API Documentation

- Document all API endpoints
- Include request/response examples
- Specify authentication requirements
- Note any rate limits or constraints

## Security

### Reporting Security Issues

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead, email security concerns to: [maintainer email]

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Security Best Practices

- Never commit API keys or secrets
- Use environment variables for sensitive data
- Validate and sanitize all user inputs
- Keep dependencies up to date
- Follow OWASP guidelines

## Community

### Getting Help

- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Report bugs via GitHub Issues
- **Email**: Contact maintainers for private matters

### Staying Updated

- Watch the repository for updates
- Follow project roadmap
- Participate in discussions
- Review other pull requests

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Recognition

Contributors will be recognized in:

- Project README
- Release notes
- Contributors page (coming soon)

Thank you for contributing to making democracy more accessible through technology!

---

**Questions?** Open a GitHub Discussion or reach out to the maintainers.
