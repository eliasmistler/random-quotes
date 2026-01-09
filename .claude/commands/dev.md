Start the development servers and open the frontend in the browser.

1. Start the backend server in the background:
   ```bash
   cd backend && uv run uvicorn app.main:app --reload --port 8000
   ```

2. Start the frontend dev server in the background:
   ```bash
   cd frontend && npm run dev
   ```

3. Wait a few seconds for servers to start, then open http://localhost:5173 in the default browser

Run both servers as background processes so they can run simultaneously. Inform the user of the URLs:
- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
