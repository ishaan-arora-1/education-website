# Contributing to Alpha One Labs Education Platform

First off, thank you for considering contributing to Alpha One Labs! It's people like you that make Alpha One Labs such a great tool for education.

This document provides guidelines and steps for contributing. Following these guidelines helps communicate that you respect the time of the developers managing and developing this open source project. In return, they should reciprocate that respect in addressing your issue, assessing changes, and helping you finalize your pull requests.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [contact@alphaonelabs.com](mailto:contact@alphaonelabs.com).

## Getting Started

### Prerequisites

Before you begin:

1. Ensure you have a [GitHub account](https://github.com/signup)
2. Read our [README.md](README.md) for project setup instructions
3. Familiarize yourself with our tech stack:
   - Python 3.10+
   - Django 4.x
   - Tailwind CSS
   - Alpine.js

### Development Environment

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone git@github.com:your-username/education-website.git
   cd education-website
   ```
3. Create a branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Making Changes

### Coding Standards

We follow these coding standards:

1. **Python Code**:

   - Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
   - Use [Black](https://github.com/psf/black) for code formatting
   - Sort imports using [isort](https://pycqa.github.io/isort/)
   - Maximum line length is 88 characters (Black default)

2. **JavaScript Code**:

   - Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
   - Use ESLint for linting

3. **HTML/Templates**:

   - Use semantic HTML5 elements
   - Follow BEM methodology for CSS classes
   - Maintain consistent indentation (2 spaces)

4. **CSS/Tailwind**:
   - Follow Tailwind CSS best practices
   - Use utility classes over custom CSS when possible
   - Maintain a consistent color scheme using theme colors

### Documentation

- Add docstrings to all Python functions, classes, and modules
- Update README.md if adding new features or changing existing ones
- Include comments for complex logic
- Document all API endpoints using docstrings

### Testing

1. Write tests for new features:
   ```bash
   python manage.py test
   ```
2. Ensure all existing tests pass
3. Add integration tests for new features
4. Include test cases for edge cases and error conditions

### Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks

Example:

```
feat(auth): add social authentication support

Add Google and GitHub OAuth support for user authentication.
Includes:
- OAuth2 integration
- User profile sync
- Test coverage

Closes #123
```

## Pull Request Process

1. **Update Documentation**:

   - Add/update docstrings
   - Update README.md if needed
   - Add comments for complex logic

2. **Run Tests**:

   ```bash
   python manage.py test
   pre-commit run --all-files
   ```

3. **Create Pull Request**:

   - Use a clear, descriptive title
   - Reference any related issues
   - Describe your changes in detail
   - Include screenshots for UI changes
   - List any dependencies added/removed

4. **Code Review**:

   - Address reviewer comments
   - Make requested changes
   - Keep the PR focused and small

5. **Merge Requirements**:
   - All tests must pass
   - Code review approval required
   - No merge conflicts
   - Documentation updated
   - Pre-commit hooks pass

## License

By contributing, you agree that your contributions will be licensed under the AGPLv3 License.

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Alpine.js Documentation](https://alpinejs.dev/docs)
- [Git Flow](https://nvie.com/posts/a-successful-git-branching-model/)

## Questions or Need Help?

- Create an issue for bugs or feature requests
- Join our community chat (coming soon)
- Email us at [contact@alphaonelabs.com](mailto:contact@alphaonelabs.com)

Thank you for contributing to Alpha One Labs! 🎉
