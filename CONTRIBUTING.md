# Contributing to AutoBug

Thank you for your interest in contributing to AutoBug! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue on GitHub with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

### Suggesting Features

Feature requests are welcome! Please open an issue describing:
- The feature you'd like to see
- Why it would be useful
- Any implementation ideas you have

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** if applicable
4. **Update documentation** if you're changing functionality
5. **Ensure tests pass** by running the test suite
6. **Submit a pull request** with a clear description of your changes

## Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/auto_bug_web.git
   cd auto_bug_web
   ```

2. Set up the development environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. Install scanning tools (see [INSTALL_TOOLS.md](INSTALL_TOOLS.md))

4. Set up the database:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   alembic upgrade head
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions focused and modular

## Testing

Before submitting a PR:
```bash
# Run tests
pytest

# Check code formatting
black --check src/

# Run linter
flake8 src/
```

## Code of Conduct

- Be respectful and constructive
- Focus on what's best for the community
- Show empathy towards other contributors

## Questions?

Feel free to open an issue for questions or join discussions on existing issues.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
