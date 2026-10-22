# College Faculty Management System

Full-stack case study: HTML + CSS + JavaScript frontend, Python FastAPI REST backend, MySQL database,
and a GenAI layer with a **single agent** (tool use) and a **multi-agent** team.

```
faculty-management-system/
├── backend/
│   ├── main.py            <- REST API (FastAPI)
│   ├── agents.py          <- Single agent + multi-agent GenAI code
│   ├── models.py          <- MySQL tables (SQLAlchemy)
│   ├── database.py        <- DB connection
│   ├── seed.py            <- Sample data (auto-loaded on first run)
│   ├── requirements.txt
│   └── .env.example
├── database/schema.sql    <- creates the empty database
└── frontend/              <- index.html, style.css, app.js
```

## Step 1: Install the tools (one time)
1. **VS Code**: https://code.visualstudio.com
2. **Python 3.10+**: https://www.python.org/downloads (Windows: tick "Add Python to PATH")
3. **MySQL Community Server + Workbench**: https://dev.mysql.com/downloads/installer (remember your root password)
4. VS Code extensions: *Python* (Microsoft), *Live Server* (Ritwick Dey), *MySQL* (optional)
5. (Optional, for the AI tab) an API key from https://console.anthropic.com

## Step 2: Open the project
VS Code -> File -> Open Folder -> choose `faculty-management-system`. Open the terminal with Ctrl + `

## Step 3: Create the database
Open MySQL Workbench, connect, open `database/schema.sql`, and click the lightning bolt to run it.
(Or in a terminal: `mysql -u root -p < database/schema.sql`)

## Step 4: Set up the backend
```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac / Linux:
source venv/bin/activate

pip install -r requirements.txt
```
Then copy `.env.example` to a new file named `.env` and fill in:
- `DB_PASSWORD` = your MySQL root password
- `ANTHROPIC_API_KEY` = your key (leave empty to use demo mode)

## Step 5: Run the backend
```bash
uvicorn main:app --reload
```
Tables and sample data are created automatically. Check it at:
- http://127.0.0.1:8000/docs (interactive API documentation, good to show in your demo)

## Step 6: Run the frontend
Right-click `frontend/index.html` in VS Code -> **Open with Live Server**.
The site opens at http://127.0.0.1:5500 and talks to the backend on port 8000.

## Step 7: Demo flow
1. Dashboard: counts and teaching-load bars.
2. Faculty: add, edit, delete.
3. Courses: assign a teacher from the dropdown, watch the dashboard load change.
4. Leave requests: submit, then approve or reject.
5. AI assistant -> Single agent: "Who is the most overloaded faculty member?"
   (the small green-lined steps show which database tools the agent chose).
6. AI assistant -> Multi-agent: Workload agent + Leave agent -> Coordinator writes the plan.

## Common errors
| Problem | Fix |
|---|---|
| `Access denied for user 'root'` | Wrong `DB_PASSWORD` in `.env` |
| `Unknown database 'faculty_db'` | Run Step 3 |
| `Failed to fetch` in the browser | Backend not running, or `API` in `frontend/app.js` has a different port |
| `cryptography` / auth plugin error | `pip install cryptography` (already in requirements) |
| AI tab says "DEMO MODE" | `ANTHROPIC_API_KEY` is empty in `.env`; restart uvicorn after editing |
