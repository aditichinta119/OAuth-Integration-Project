# OAuth Integration Project

This is a full-stack OAuth 2.0 integration app using FastAPI (backend) and React (frontend). It connects with Airtable, Notion, and HubSpot, handles token storage in Redis, and fetches data using their APIs.

## How to Run

1. Clone the repo, start Redis, and run the backend:

```bash
git clone https://github.com/your-username/OAuth-Integration-Project.git
cd OAuth-Integration-Project
```
2. Start Redis (use Docker or make sure it's running locally)
```bash
docker run -p 6379:6379 redis
```
3. Run the backend
```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

4. In a new terminal, start the frontend:
```bash
cd frontend
npm install
npm start
```
Frontend will run at: http://localhost:3000
