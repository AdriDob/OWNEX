# Contributing to OWNEX

Thank you for your interest in contributing to OWNEX! We welcome contributions from the community.

## 🎯 How to Contribute

### Reporting Bugs

- Search existing issues to avoid duplicates
- Use the [GitHub Issues](https://github.com/AdriDob/rastrohunteralpha/issues) 
- Include:
  - Clear title and description
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details (OS, Python version, etc.)

### Suggesting Features

- Use [GitHub Discussions](https://github.com/AdriDob/rastrohunteralpha/discussions) for major features
- For smaller features, use GitHub Issues with the `enhancement` label
- Include:
  - Problem statement
  - Proposed solution
  - Alternative approaches considered

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Ensure tests pass (`python scripts/dev test`)
5. Ensure linting passes (`python scripts/dev check`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 🛠️ Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/rastrohunteralpha.git
cd rastrohunteralpha

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python scripts/dev test

# Run linting
python scripts/dev check
```

## 📋 Code Style

- Follow existing code style (enforced by Ruff)
- Write docstrings for functions and classes
- Keep functions focused and small
- Add tests for new features
- Ensure all tests pass before submitting

## 🧪 Testing

- Write tests for new functionality
- Ensure existing tests still pass
- Test on Python 3.11+
- Use pytest for backend tests
- Use Vitest for frontend tests

## 📝 Commit Messages

Follow conventional commit format:

```
feat: add new feature
fix: resolve bug in authentication
docs: update README
style: format code with ruff
refactor: simplify function logic
test: add unit tests for dashboard
chore: update dependencies
```

## 🤝 Code of Conduct

- Be respectful and inclusive
- Focus on what is best for the community
- Show empathy towards other community members

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Happy contributing! 🚀**
