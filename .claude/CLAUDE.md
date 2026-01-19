# Random Quotes

## Project Overview

<!-- Describe your project here -->

## Tech Stack

### Backend
- Python 3.14
- FastAPI for web API
- Pydantic for all data structures and validation
- toolz for functional programming utilities
- uv for dependency management
- pytest for testing

### Frontend
- Vue 3 with Composition API
- TypeScript
- Vite for build tooling
- Vue Router for routing
- Pinia for state management
- ESLint + Prettier for linting/formatting

## Project Structure

```
ransom-notes/
├── backend/                 # Python backend (FastAPI)
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic (pure functions)
│   │   ├── config.py       # Application configuration
│   │   └── main.py         # FastAPI app entry point
│   ├── tests/              # pytest tests
│   ├── pyproject.toml      # Python dependencies
│   └── .pre-commit-config.yaml
├── frontend/               # Vue 3 frontend
│   ├── src/
│   │   ├── components/     # Vue components
│   │   ├── views/          # Page components
│   │   ├── stores/         # Pinia stores
│   │   ├── router/         # Vue Router config
│   │   └── App.vue         # Root component
│   ├── package.json        # Node dependencies
│   └── vite.config.ts      # Vite configuration
└── README.md
```

## Development Environment

### IDE Setup

- **IDE**: [PyCharm](https://www.jetbrains.com/pycharm/) with Vue.js plugin
- **Browser**: Vue.js devtools extension ([Chrome](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/))

### MCP Servers

- **Chrome DevTools MCP**: Browser debugging and automation for frontend development
  ```bash
  # Add the server (run once)
  claude mcp add --transport stdio chrome-devtools -- npx -y chrome-devtools-mcp@latest

  # For authenticated sessions, start Chrome with remote debugging first:
  chrome --remote-debugging-port=9222 --user-data-dir="path/to/debug-profile"
  ```

### Manual Testing & Browser Automation

**Always use Docker Compose for manual testing or Chrome MCP testing.** This ensures consistent environments and avoids port conflicts between agent worktrees.

```bash
# From any worktree directory
docker-compose up --build

# Frontend: http://localhost:80
# Backend API: http://localhost:8000
```

Using Docker Compose provides:
- Consistent port mappings across all agents
- Production-like environment
- No need to install dependencies locally in each worktree
- Proper nginx configuration for frontend/backend routing

## Development

### Backend Commands

All backend commands must be run from the `backend/` directory:

```bash
cd backend
uv run pytest              # Run tests
uv run pre-commit run --all-files  # Run linters
uv run uvicorn app.main:app --reload  # Start dev server
```

### Frontend Commands

All frontend commands must be run from the `frontend/` directory:

```bash
cd frontend
npm install                # Install dependencies
npm run dev                # Start dev server (http://localhost:5173)
npm run build              # Build for production
npm run lint               # Run ESLint
npm run format             # Run Prettier
```

### Slash Commands

- `/dev` - Start backend and frontend servers, open browser

- `/ship` - Run tests, commit, create PR, merge, and clean up (see Multi-Agent Workflow)

## Multi-Agent Workflow

This project uses **git worktrees** for multi-agent development, allowing multiple Claude agents to work concurrently in isolated directories without conflicts.

### Directory Structure

Each agent works in its own worktree directory:

```
PycharmProjects/
├── ransom-notes/              # Main repo (master branch)
├── ransom-notes-agent1/       # Agent 1's worktree
├── ransom-notes-agent2/       # Agent 2's worktree
└── ransom-notes-agent3/       # Agent 3's worktree
```

### Setting Up a New Agent Worktree

From the main repo directory (`ransom-notes/`):

```bash
# Create a new branch and worktree for an agent
git worktree add ../ransom-notes-<agent-name> -b ransom-notes-<agent-name>

# Example for agent2:
git worktree add ../ransom-notes-agent2 -b ransom-notes-agent2
```

### Agent Workflow

**As an agent, you should:**

1. **Work in your assigned worktree directory:**
   ```bash
   cd ../ransom-notes-<agent-name>
   ```

2. **Make commits as needed** on your branch (each worktree has its own branch)

3. **When ready to ship (`/ship` command):**
   - Run all tests
   - Commit any remaining changes
   - Pull latest from master and rebase:
     ```bash
     git fetch origin master
     git rebase origin/master
     ```
   - Push your branch and create PR:
     ```bash
     git push -u origin ransom-notes-<agent-name>
     gh pr create --fill --base master
     gh pr merge --merge --delete-branch
     ```

4. **After merging, reset your worktree to master:**
   ```bash
   git fetch origin master
   git reset --hard origin/master
   ```

### Removing a Worktree

When an agent is no longer needed:

```bash
# From the main repo directory
git worktree remove ../ransom-notes-<agent-name>
git branch -d ransom-notes-<agent-name>
```

### Important Notes

- Each agent has its own isolated directory - no file conflicts between agents
- Worktrees share the same `.git` database, so branches are visible across all worktrees
- Always work in your assigned worktree, never directly on master in the main repo
- Keep changes small and merge frequently to minimize rebase conflicts
- The main `ransom-notes/` directory should stay on master for reference

### Code Style

- **Backend**: Linting/formatting with ruff (line length: 120), pre-commit hooks enforced
- **Frontend**: ESLint + Prettier enforced

## Architecture

This is a real-time multiplayer game with:
- **Backend**: Python FastAPI REST API + WebSocket for real-time communication
- **Frontend**: Vue 3 SPA with TypeScript

## Coding Paradigm

Follow a **functional-first, pragmatic** approach:

### Functional Programming Principles

- Prefer pure functions with no side effects
- Use immutable data structures (Pydantic models are immutable by default)
- Leverage `toolz` for functional utilities: `pipe`, `curry`, `compose`, `map`, `filter`, `reduce`, `partial`, etc.
- Avoid classes for logic; use them only for data (Pydantic models) or when truly necessary
- Keep functions small and focused on a single responsibility
- Use function composition to build complex behavior from simple parts

### Vue 3 Composition API Style

- Use `<script setup lang="ts">` for components
- Prefer composables over mixins
- Use `ref` and `computed` for reactive state
- Keep components small and focused

### Data Structures

- Use **Pydantic models** for all structured data (backend)
- Use **TypeScript interfaces** for all structured data (frontend)
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
