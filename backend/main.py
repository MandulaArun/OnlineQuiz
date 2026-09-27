import os
import random
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sklearn.linear_model import LogisticRegression

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "quiz.db"
FRONTEND_DIR = BASE_DIR / "frontend"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            difficulty INTEGER NOT NULL,
            is_correct INTEGER NOT NULL,
            time_spent REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )

    conn.commit()
    conn.close()


class QuizQuestion(BaseModel):
    id: int
    text: str
    options: List[str]
    correct_index: int
    topic: str
    difficulty: int  # 1 = easy, 2 = medium, 3 = hard


class PublicQuestion(BaseModel):
    id: int
    text: str
    options: List[str]
    topic: str
    difficulty: int


class AnswerPayload(BaseModel):
    question_id: int
    selected_index: int
    time_spent: Optional[float] = None


class QuizSubmission(BaseModel):
    username: str
    answers: List[AnswerPayload]


class QuestionFeedback(BaseModel):
    question_id: int
    correct: bool
    correct_index: int


class QuizResult(BaseModel):
    total_questions: int
    correct_answers: int
    score_percent: float
    feedback: List[QuestionFeedback]


class TopicPerformance(BaseModel):
    topic: str
    total: int
    correct: int
    accuracy: float


class PerformanceSummary(BaseModel):
    username: str
    total_answers: int
    overall_accuracy: Optional[float]
    topics: List[TopicPerformance]
    suggestions: List[str]


class DifficultyOption(BaseModel):
    value: int
    label: str


class CatalogResponse(BaseModel):
    topics: List[str]
    difficulties: List[DifficultyOption]
    default_limit: int


# In-memory question bank with topics and difficulty levels
QUESTION_BANK: List[QuizQuestion] = [
    QuizQuestion(
        id=1,
        text="What is the time complexity of binary search on a sorted array?",
        options=["O(n)", "O(log n)", "O(n log n)", "O(1)"],
        correct_index=1,
        topic="Algorithms",
        difficulty=1,
    ),
    QuizQuestion(
        id=2,
        text="Which HTTP method is idempotent and typically used for updates?",
        options=["POST", "PUT", "PATCH", "CONNECT"],
        correct_index=1,
        topic="Web",
        difficulty=1,
    ),
    QuizQuestion(
        id=3,
        text="In Python, what does the `@` operator do for NumPy arrays?",
        options=[
            "Element-wise addition",
            "Element-wise multiplication",
            "Matrix multiplication",
            "Bitwise AND",
        ],
        correct_index=2,
        topic="Python",
        difficulty=2,
    ),
    QuizQuestion(
        id=4,
        text="Which of the following is NOT a typical activation function in neural networks?",
        options=["ReLU", "Sigmoid", "Softmax", "Fourier"],
        correct_index=3,
        topic="Machine Learning",
        difficulty=2,
    ),
    QuizQuestion(
        id=5,
        text="What does Docker primarily provide?",
        options=[
            "Operating system virtualization",
            "Lightweight containerization",
            "Hardware emulation",
            "Code version control",
        ],
        correct_index=1,
        topic="DevOps",
        difficulty=1,
    ),
    QuizQuestion(
        id=6,
        text="In a RESTful API, which status code usually indicates that a resource was successfully created?",
        options=["200 OK", "201 Created", "204 No Content", "400 Bad Request"],
        correct_index=1,
        topic="Web",
        difficulty=1,
    ),
    QuizQuestion(
        id=7,
        text="Which algorithm is commonly used for gradient-based optimization in deep learning?",
        options=["K-Means", "Adam", "Apriori", "Dijkstra"],
        correct_index=1,
        topic="Machine Learning",
        difficulty=2,
    ),
    QuizQuestion(
        id=8,
        text="Which database transaction property ensures that once a transaction is committed, it remains so?",
        options=["Atomicity", "Consistency", "Isolation", "Durability"],
        correct_index=3,
        topic="Databases",
        difficulty=2,
    ),
    QuizQuestion(
        id=9,
        text="What is the purpose of a Kubernetes Deployment?",
        options=[
            "Manage and scale Pods",
            "Store application logs",
            "Provide DNS resolution",
            "Handle network policies",
        ],
        correct_index=0,
        topic="DevOps",
        difficulty=3,
    ),
    QuizQuestion(
        id=10,
        text="In FastAPI, which object is used to define the web application?",
        options=["Flask", "APIRouter", "FastAPI", "WSGIApp"],
        correct_index=2,
        topic="Python",
        difficulty=1,
    ),
]


TOPICS = sorted({q.topic for q in QUESTION_BANK})
TOPIC_INDEX = {topic: idx for idx, topic in enumerate(TOPICS)}

DIFFICULTY_LABELS = {
    1: "Easy",
    2: "Medium",
    3: "Hard",
}


app = FastAPI(title="Online Quiz Application", version="1.0.0")

# CORS (safe defaults; frontend can be served separately if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and root HTML
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR), html=False), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/", include_in_schema=False)
def read_root() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(str(index_path))


@app.get("/api/questions", response_model=List[PublicQuestion])
def get_questions(
    topic: Optional[str] = None,
    difficulty: Optional[int] = None,
    limit: Optional[int] = Query(
        None,
        ge=1,
        description="Maximum number of questions to return (randomly sampled).",
    ),
) -> List[PublicQuestion]:
    """
    Return quiz questions without exposing correct answers.

    Real-world behaviour:
    - Filter by topic and/or difficulty if provided.
    - Randomize question order.
    - Optionally limit the number of returned questions.
    """
    filtered: List[QuizQuestion] = []
    for q in QUESTION_BANK:
        if topic and q.topic != topic:
            continue
        if difficulty and q.difficulty != difficulty:
            continue
        filtered.append(q)

    if not filtered:
        # Fallback: if filters produce no questions, return all so the user is not stuck.
        filtered = list(QUESTION_BANK)

    random.shuffle(filtered)

    if limit is not None:
        filtered = filtered[: limit]

    return [
        PublicQuestion(
            id=q.id,
            text=q.text,
            options=q.options,
            topic=q.topic,
            difficulty=q.difficulty,
        )
        for q in filtered
    ]


@app.get("/api/catalog", response_model=CatalogResponse)
def get_catalog() -> CatalogResponse:
    """
    Return available quiz configuration options (topics, difficulties, defaults).
    """
    return CatalogResponse(
        topics=TOPICS,
        difficulties=[
            DifficultyOption(value=value, label=label)
            for value, label in DIFFICULTY_LABELS.items()
        ],
        default_limit=5,
    )


def get_or_create_user_id(username: str) -> int:
    username = username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username must not be empty.")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if row:
        user_id = int(row["id"])
    else:
        cur.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
        user_id = cur.lastrowid

    conn.close()
    return user_id


def build_features(topic: str, difficulty: int) -> np.ndarray:
    """Build feature vector [difficulty] + one-hot of topic."""
    x = np.zeros(1 + len(TOPICS), dtype=float)
    x[0] = float(difficulty)
    topic_idx = TOPIC_INDEX.get(topic)
    if topic_idx is not None:
        x[1 + topic_idx] = 1.0
    return x


def train_user_model(user_id: int) -> Optional[LogisticRegression]:
    """Train a simple logistic regression model for a given user, if enough data."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT topic, difficulty, is_correct
        FROM responses
        WHERE user_id = ?
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows or len(rows) < 5:
        # Not enough data to train a robust model
        return None

    X_list: List[np.ndarray] = []
    y_list: List[int] = []

    for r in rows:
        topic = r["topic"]
        difficulty = int(r["difficulty"])
        is_correct = int(r["is_correct"])
        X_list.append(build_features(topic, difficulty))
        y_list.append(is_correct)

    X = np.vstack(X_list)
    y = np.array(y_list)

    # Handle edge case: all labels are the same
    if len(np.unique(y)) < 2:
        return None

    model = LogisticRegression(solver="liblinear")
    model.fit(X, y)
    return model


def generate_suggestions(
    username: str, user_id: int, topic_stats: List[TopicPerformance]
) -> List[str]:
    suggestions: List[str] = []

    total_answers = sum(t.total for t in topic_stats)
    if total_answers == 0:
        return [
            "Start by taking a quiz to generate your first performance profile.",
            "Try answering questions from multiple topics to let the model learn your strengths and weaknesses.",
        ]

    # Basic rule-based suggestion from topic accuracies
    weak_topics = [t for t in topic_stats if t.total >= 2 and t.accuracy < 0.7]
    weak_topics_sorted = sorted(weak_topics, key=lambda t: t.accuracy)

    if weak_topics_sorted:
        names = ", ".join(f"{t.topic} ({t.accuracy*100:.0f}% accuracy)" for t in weak_topics_sorted[:3])
        suggestions.append(
            f"Focus on these weaker topics next: {names}."
        )

    # Train ML model for more nuanced suggestions
    model = train_user_model(user_id)
    if model is None:
        if not suggestions:
            suggestions.append(
                "You have limited data so far. Keep practicing across different topics to enable personalized ML-based recommendations."
            )
        return suggestions

    # Use the model to predict success probability across (topic, difficulty) combinations
    topic_difficulty_scores: Dict[str, Dict[int, float]] = {}
    for topic in TOPICS:
        topic_scores: Dict[int, float] = {}
        for difficulty in [1, 2, 3]:
            x = build_features(topic, difficulty).reshape(1, -1)
            prob_correct = float(model.predict_proba(x)[0][1])
            topic_scores[difficulty] = prob_correct
        topic_difficulty_scores[topic] = topic_scores

    # Find worst (topic, difficulty) combinations
    candidate_pairs: List[Dict[str, Any]] = []
    for topic, scores in topic_difficulty_scores.items():
        for difficulty, prob in scores.items():
            candidate_pairs.append(
                {"topic": topic, "difficulty": difficulty, "prob": prob}
            )

    candidate_pairs.sort(key=lambda x: x["prob"])
    worst_pairs = candidate_pairs[:3]

    for pair in worst_pairs:
        topic = pair["topic"]
        difficulty = pair["difficulty"]
        prob = pair["prob"]
        label = DIFFICULTY_LABELS.get(difficulty, f"Level {difficulty}")
        suggestions.append(
            f"Your model-predicted accuracy for {topic} ({label} questions) is about {prob*100:.0f}%. "
            f"Practice a few more {label} questions in {topic} to improve."
        )

    if not suggestions:
        suggestions.append(
            "You're performing consistently across topics. Consider increasing difficulty to challenge yourself."
        )

    return suggestions


@app.post("/api/submit", response_model=QuizResult)
def submit_quiz(payload: QuizSubmission) -> QuizResult:
    if not payload.answers:
        raise HTTPException(status_code=400, detail="No answers submitted.")

    user_id = get_or_create_user_id(payload.username)

    question_lookup = {q.id: q for q in QUESTION_BANK}

    total = len(payload.answers)
    correct_count = 0
    feedback: List[QuestionFeedback] = []

    conn = get_db_connection()
    cur = conn.cursor()

    for ans in payload.answers:
        question = question_lookup.get(ans.question_id)
        if question is None:
            raise HTTPException(status_code=400, detail=f"Invalid question_id {ans.question_id}")

        is_correct = int(ans.selected_index == question.correct_index)
        if is_correct:
            correct_count += 1

        feedback.append(
            QuestionFeedback(
                question_id=question.id,
                correct=bool(is_correct),
                correct_index=question.correct_index,
            )
        )

        cur.execute(
            """
            INSERT INTO responses (user_id, question_id, topic, difficulty, is_correct, time_spent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                question.id,
                question.topic,
                question.difficulty,
                is_correct,
                ans.time_spent,
            ),
        )

    conn.commit()
    conn.close()

    score_percent = (correct_count / total) * 100.0 if total > 0 else 0.0

    return QuizResult(
        total_questions=total,
        correct_answers=correct_count,
        score_percent=round(score_percent, 2),
        feedback=feedback,
    )


@app.get("/api/performance/{username}", response_model=PerformanceSummary)
def get_performance(username: str) -> PerformanceSummary:
    username = username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username must not be empty.")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return PerformanceSummary(
            username=username,
            total_answers=0,
            overall_accuracy=None,
            topics=[],
            suggestions=[
                "No data yet for this user. Complete at least one quiz to get performance insights."
            ],
        )

    user_id = int(row["id"])

    cur.execute(
        """
        SELECT topic,
               COUNT(*) AS total,
               SUM(is_correct) AS correct
        FROM responses
        WHERE user_id = ?
        GROUP BY topic
        """,
        (user_id,),
    )
    topic_rows = cur.fetchall()

    topics: List[TopicPerformance] = []
    total_answers = 0
    total_correct = 0

    for r in topic_rows:
        total = int(r["total"])
        correct = int(r["correct"] or 0)
        accuracy = correct / total if total > 0 else 0.0
        topics.append(
            TopicPerformance(
                topic=r["topic"],
                total=total,
                correct=correct,
                accuracy=round(accuracy, 3),
            )
        )
        total_answers += total
        total_correct += correct

    overall_accuracy = (
        round(total_correct / total_answers, 3) if total_answers > 0 else None
    )

    suggestions = generate_suggestions(username, user_id, topics)

    conn.close()

    return PerformanceSummary(
        username=username,
        total_answers=total_answers,
        overall_accuracy=overall_accuracy,
        topics=topics,
        suggestions=suggestions,
    )

