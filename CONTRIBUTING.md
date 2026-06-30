# Contributing to PocketSET

First off, thanks for taking the time to contribute!

## How to Contribute

### Reporting Bugs

- Open an issue describing the bug
- Include your platform (Termux/Kali/Linux), Python version, and full error output
- Steps to reproduce are required

### Suggesting Enhancements

- Open an issue with the label `enhancement`
- Describe the feature, why it's useful, and how it should work
- Include examples if applicable

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Commit your changes (`git commit -m 'feat: add my feature'`)
4. Push to the branch (`git push origin feat/my-feature`)
5. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/highoncomputers/PocketSET.git
cd PocketSET
pip install -r requirements.txt
python3 wrapper.py
```

### Code Style

- Follow PEP 8
- Run `ruff check .` before committing (if available)
- Keep functions focused and small
- Add type hints to new code
- Include docstrings for public functions

### Testing

- Add tests for new features in `tests/`
- Run existing tests before submitting
- Test on Termux if your change affects platform detection

## Code of Conduct

This project follows a standard Code of Conduct. Be respectful, constructive, and inclusive.
