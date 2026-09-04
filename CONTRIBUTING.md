# Contributing to OpenSight Private

Thank you for your interest in contributing to OpenSight Private! We welcome contributions from everyone, regardless of experience level.

## 🎯 Ways to Contribute

### 1. **Report Bugs**
Found an issue? Help us fix it!
- Go to [Issues](../../issues)
- Click **New Issue**
- Describe the bug, steps to reproduce, and expected behavior
- Add labels like `bug`, `high-priority`, etc.

### 2. **Suggest Features**
Have a great idea? We'd love to hear it!
- Open an issue with label `enhancement`
- Explain the feature and why it would be useful
- Discuss it with the community

### 3. **Improve Documentation**
- Fix typos in README
- Add examples or tutorials
- Clarify confusing sections
- Improve code comments

### 4. **Write Code**
- Fix bugs
- Implement features
- Optimize performance
- Add tests

### 5. **Help Others**
- Answer questions in [Discussions](../../discussions)
- Help newcomers get started
- Share use cases and tips

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Git
- GitHub account

### Setup Development Environment

```bash
# 1. Fork the repository
# Click "Fork" on https://github.com/mkaramrashid2012-code/open-sight

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/open-sight.git
cd open-sight

# 3. Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 4. Install dependencies (including dev tools)
pip install -r requirements.txt
pip install pytest pytest-cov black flake8  # Dev tools

# 5. Create a new branch for your work
git checkout -b feature/my-feature
# or
git checkout -b fix/bug-name
```

---

## 📝 Development Workflow

### 1. Make Your Changes
```bash
# Edit files in your favorite editor
# Keep changes focused on one feature/bug
```

### 2. Test Your Changes
```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=backend tests/

# Run specific test
pytest tests/test_tracking.py -v
```

### 3. Format Code
```bash
# Format with black (Python formatter)
black backend/

# Check with flake8 (linter)
flake8 backend/
```

### 4. Commit Your Changes
```bash
# Follow conventional commits
git add .
git commit -m "feat: add new tracking feature"
# or
git commit -m "fix: resolve tracking state machine bug"
# or
git commit -m "docs: improve README installation guide"
```

Commit types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Test additions
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `chore:` - Maintenance

### 5. Push and Create Pull Request
```bash
git push origin feature/my-feature
```

Then open a Pull Request on GitHub with:
- Clear title describing the change
- Description of what you changed and why
- Reference to related issues (e.g., `Closes #42`)
- Screenshots/videos if applicable

---

## 📋 Pull Request Checklist

Before submitting a PR, make sure:

- [ ] Tests pass: `pytest`
- [ ] Code is formatted: `black backend/`
- [ ] No linting errors: `flake8 backend/`
- [ ] New tests added for new features
- [ ] Documentation updated if needed
- [ ] Commit messages are clear and descriptive
- [ ] No secrets or credentials in code
- [ ] PR description explains the changes

---

## 🏗️ Project Structure

```
open-sight/
├── backend/
│   ├── tracking/           # Object tracking logic
│   ├── search/             # Search engine
│   ├── security/           # Audit logging
│   ├── cases/              # Case management
│   ├── retention/          # Data retention
│   └── evidence/           # Evidence export
├── tests/                  # Unit tests
├── database/               # Schema
└── run_demo.py             # Demo runner
```

---

## 🧪 Testing Guidelines

All new features should have tests:

```python
# tests/test_my_feature.py
import pytest
from backend.my_module import my_function

def test_my_function_basic():
    """Test basic functionality"""
    result = my_function(input_data)
    assert result == expected_output

def test_my_function_edge_case():
    """Test edge cases"""
    result = my_function(edge_case_data)
    assert result == expected_result
```

Run tests:
```bash
pytest tests/ -v
```

---

## 📚 Code Style

### Python Style Guide
- Follow [PEP 8](https://pep8.org/)
- Use type hints where possible
- Write clear variable and function names
- Add docstrings to functions

### Example
```python
def calculate_track_quality(confidence: float, continuity: float, smoothness: float) -> float:
    """
    Calculate overall track quality score.
    
    Args:
        confidence: Detection confidence (0-1)
        continuity: Track continuity score (0-1)
        smoothness: Trajectory smoothness score (0-1)
    
    Returns:
        Quality score (0-1)
    """
    return (confidence + continuity + smoothness) / 3
```

---

## 🐛 Reporting Bugs

When reporting bugs, include:

1. **Description** - What happened?
2. **Steps to Reproduce** - How to recreate the bug
3. **Expected Behavior** - What should happen
4. **Actual Behavior** - What actually happened
5. **Environment** - OS, Python version, etc.
6. **Error Message** - Full traceback if available
7. **Screenshots/Logs** - If applicable

Example:
```
**Description:** Demo crashes when running with empty input

**Steps to Reproduce:**
1. Run `python run_demo.py` with no arguments
2. Press Enter

**Expected:** Demo runs successfully
**Actual:** Crashes with KeyError

**Environment:**
- OS: Windows 10
- Python: 3.11
- Branch: main

**Error:**
```
KeyError: 'tracks'
Traceback: ...
```
```

---

## ✨ Feature Requests

When suggesting features, explain:

1. **Problem** - What problem does it solve?
2. **Solution** - How should it work?
3. **Example** - Use case or example
4. **Benefits** - Why would users want this?

---

## 💬 Community

- **Discussions** - Ask questions and share ideas
- **Issues** - Report bugs and request features
- **Pull Requests** - Contribute code
- **Email** - mkaramrashid2012@gmail.com

---

## 📖 Resources

- [GitHub Guides](https://guides.github.com/)
- [Git Cheat Sheet](https://github.github.com/training-kit/downloads/github-git-cheat-sheet.pdf)
- [Python Best Practices](https://pep8.org/)
- [pytest Documentation](https://docs.pytest.org/)

---

## 🙏 Thank You!

Your contributions make OpenSight Private better for everyone. We appreciate:
- Bug reports
- Feature suggestions
- Documentation improvements
- Code contributions
- Spreading the word!

**Questions?** Open a discussion or email us!

---

**Happy coding! 🚀**
