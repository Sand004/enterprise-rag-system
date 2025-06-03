# Contributing to Enterprise RAG System

We welcome contributions to the Enterprise RAG System! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Respect differing viewpoints and experiences

## Getting Started

### Prerequisites

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/enterprise-rag-system.git
   cd enterprise-rag-system
   ```
3. Set up development environment:
   ```bash
   ./scripts/init_system.sh
   make dev-up
   ```

### Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and update PLANNING_AND_TASKS.md

3. Write/update tests:
   ```bash
   make test
   ```

4. Format your code:
   ```bash
   make format
   ```

5. Run linting:
   ```bash
   make lint
   ```

6. Commit your changes:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

7. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

8. Create a Pull Request

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

## Code Style

### Python

- Follow PEP 8
- Use Black for formatting
- Use type hints
- Write docstrings for all public functions

### Example:

```python
def process_document(file_path: str, options: Dict[str, Any]) -> ProcessedDocument:
    """Process a document file.
    
    Args:
        file_path: Path to the document file
        options: Processing options
        
    Returns:
        ProcessedDocument: The processed document object
        
    Raises:
        ValueError: If file_path is invalid
        ProcessingError: If processing fails
    """
    # Implementation
```

## Testing

### Writing Tests

- Write unit tests for all new functionality
- Maintain test coverage above 80%
- Use pytest fixtures for common test data
- Mock external dependencies

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test file
pytest tests/unit/test_document_processor.py
```

## Documentation

- Update relevant documentation for any changes
- Add docstrings to all new functions and classes
- Update API documentation if endpoints change
- Include examples in documentation

## Pull Request Process

1. **Update PLANNING_AND_TASKS.md**: Document your changes
2. **Ensure tests pass**: All tests must pass
3. **Update documentation**: Keep docs in sync with code
4. **Request review**: Tag relevant maintainers
5. **Address feedback**: Respond to review comments
6. **Squash commits**: Clean up commit history if requested

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] PLANNING_AND_TASKS.md is updated
- [ ] Commit messages follow conventions
- [ ] No sensitive data is included

## Architecture Guidelines

### Adding New Features

1. Discuss major features in an issue first
2. Follow existing architectural patterns
3. Keep components loosely coupled
4. Write comprehensive tests
5. Document design decisions

### Performance Considerations

- Profile code for performance bottlenecks
- Use async operations where appropriate
- Implement proper caching strategies
- Consider memory usage for large documents

## Security Guidelines

- Never commit secrets or credentials
- Use environment variables for configuration
- Validate all user inputs
- Follow OWASP best practices
- Report security issues privately

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release PR
4. Tag release after merge
5. Deploy to staging first
6. Monitor for issues
7. Deploy to production

## Getting Help

- Check existing issues and discussions
- Join our Discord server
- Attend community meetings
- Ask questions in PR comments

## Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to Enterprise RAG System!