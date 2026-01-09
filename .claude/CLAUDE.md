# Ransom Notes

## Project Overview

<!-- Describe your project here -->

## Tech Stack

- Python 3.14
- FastAPI for web API
- Pydantic for all data structures and validation
- toolz for functional programming utilities
- uv for dependency management
- pytest for testing

## Development

### Commands

- `uv run pytest` - Run tests
- `uv run pre-commit run --all-files` - Run linters
- `/ship` - Run tests, commit, and push to master

### Code Style

- Linting/formatting with ruff (line length: 88)
- Pre-commit hooks enforced

## Architecture

<!-- Describe your architecture here -->

## Coding Paradigm

Follow a **functional-first, pragmatic** approach:

### Functional Programming Principles

- Prefer pure functions with no side effects
- Use immutable data structures (Pydantic models are immutable by default)
- Leverage `toolz` for functional utilities: `pipe`, `curry`, `compose`, `map`, `filter`, `reduce`, `partial`, etc.
- Avoid classes for logic; use them only for data (Pydantic models) or when truly necessary
- Keep functions small and focused on a single responsibility
- Use function composition to build complex behavior from simple parts

### Data Structures

- Use **Pydantic models** for all structured data
- Prefer dataclasses or Pydantic over dicts for typed data
- Validate at the boundaries, trust the types internally

### Pragmatic Exceptions

- Use classes when the domain genuinely calls for it (e.g., stateful resources, context managers)
- Don't over-abstract; simple, readable code beats clever functional one-liners
- Performance-critical code may deviate when necessary

## Testing

### Test-Driven Development (TDD)

Follow a strict TDD workflow:

1. **Write the test first** - Define expected behavior before implementation
2. **Run the test** - Verify it fails for the right reason
3. **Implement minimally** - Write just enough code to pass the test
4. **Refactor** - Clean up while keeping tests green
5. **Repeat**

### Testing Guidelines

- Heavy reliance on pytest for all testing
- Write tests for every new function and feature
- Test edge cases and error conditions
- Use pytest fixtures for setup and teardown
- Prefer small, focused tests over large integration tests
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`

---

**Note to Claude:** Keep this file up to date. When architectural decisions are made, new conventions are established, or project structure changes, update this document to reflect the current state. This file should always accurately represent the project's standards and practices.
