# Ransom Notes

A digital implementation of the popular party game Ransom Notes, featuring a TypeScript frontend and Python backend.

## About the Game

Ransom Notes is a creative party game where players construct responses to prompts using a limited set of random word tiles. Each round, a prompt card is revealed and players must piece together the funniest or most fitting answer using only the words available to them. A rotating judge picks the best response, and the first player to win five rounds wins the game.

The game captures the humor and creativity of crafting messages from mismatched words—like a classic ransom note—leading to hilarious and unexpected answers.

## Tech Stack

- **Frontend**: TypeScript
- **Backend**: Python 3.14, FastAPI, Pydantic
- **Package Management**: uv

## Getting Started

### Prerequisites

- Python 3.14+
- Node.js (for frontend)
- uv (Python package manager)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ransom-notes

# Install backend dependencies
cd backend
uv sync

# Install frontend dependencies (when available)
cd ../frontend
npm install
```

### Running the Application

```bash
# Start the backend (from backend/ directory)
cd backend
uv run uvicorn app.main:app --reload

# Start the frontend (in another terminal, when available)
cd frontend
npm run dev
```

## Development

### IDE Setup

- [PyCharm](https://www.jetbrains.com/pycharm/) with Vue.js plugin for full-stack development
- Vue.js devtools browser extension ([Chrome](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/))

### Backend Commands

Run from the `backend/` directory:

- `uv run pytest` - Run tests
- `uv run pre-commit run --all-files` - Run linters

### Code Style

- Python: Linting and formatting with ruff (line length: 120)
- Pre-commit hooks enforced

## License

MIT
