# Online Quiz Application

This is a full-stack **Online Quiz Application** built with:

- **Frontend**: HTML, CSS, and vanilla JavaScript
- **Backend**: Python with FastAPI
- **Database**: SQLite (via Python `sqlite3`)
- **Machine Learning**: `scikit-learn` for performance modeling and improvement suggestions

The app lets users:

- Take multiple-choice quizzes
- Track performance over time
- Receive **ML-based suggestions** on which topics and difficulty levels to focus on

---

## 1. Project Structure

- **`backend/`**
  - `main.py` – FastAPI app, API endpoints, ML integration, and DB handling
- **`frontend/`**
  - `index.html` – main UI
  - `styles.css` – modern responsive styling
  - `app.js` – quiz logic and API calls
- **`requirements.txt`** – Python dependencies

---

## 2. Setup Instructions

### 2.1. Create and activate a virtual environment (recommended)

From the project root (`cloudcomp`):

```bash
python -m venv .venv
.venv\Scripts\activate
```

If you are on PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2.2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 3. Running the Backend (FastAPI)

From the project root:

```bash
cd backend
uvicorn main:app --reload
```

The API and frontend will be available at:

- `http://127.0.0.1:8000/` – main quiz UI
- `http://127.0.0.1:8000/docs` – interactive API docs (Swagger UI)

---

## 4. Features

- **User identification** via username (no password, demo-only)
- **Quiz questions** with topic and difficulty metadata
- **Performance tracking**:
  - Stores each answer with correctness and metadata
  - Computes overall and per-topic accuracy
- **Machine Learning integration**:
  - Uses `scikit-learn` Logistic Regression to model the probability of correct answers
  - Suggests **weak topics** and appropriate difficulty levels to practice
- **Modern UI**:
  - Responsive layout
  - Card-based quiz interface
  - Real-time feedback and performance summary

---

## 5. Frontend Development Notes

- The frontend is served directly by FastAPI:
  - `index.html` is returned at `/`
  - Static assets (`styles.css`, `app.js`) are served from `/static/*`
- All API calls in `app.js` use relative paths (e.g., `/api/questions`, `/api/submit`, `/api/performance/{username}`), so no manual CORS configuration is required if you use the built-in server.

---

## 6. Extending the App

Ideas for extension:

- Add user authentication (JWT or session-based)
- Add more topics and question banks, persisted in the database
- Add time-based performance trends (charts over time)
- Export user performance reports (PDF/CSV)
- Deploy the app using Docker / a cloud platform (e.g., Azure, AWS, or Heroku alternatives)

