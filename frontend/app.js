const API_BASE = "";

let questions = [];
let currentQuestionIndex = 0;
let answers = [];
let questionStartTime = null;

const usernameInput = document.getElementById("username");
const saveUsernameBtn = document.getElementById("save-username");
const questionCounter = document.getElementById("question-counter");
const questionTopic = document.getElementById("question-topic");
const questionDifficulty = document.getElementById("question-difficulty");
const questionTextEl = document.getElementById("question-text");
const optionsContainer = document.getElementById("options-container");
const prevBtn = document.getElementById("prev-question");
const nextBtn = document.getElementById("next-question");
const startQuizBtn = document.getElementById("start-quiz");
const submitQuizBtn = document.getElementById("submit-quiz");
const scoreSummaryEl = document.getElementById("score-summary");
const performanceSummaryEl = document.getElementById("performance-summary");
const suggestionsListEl = document.getElementById("suggestions-list");
const toastEl = document.getElementById("toast");
const topicSelect = document.getElementById("topic-select");
const difficultySelect = document.getElementById("difficulty-select");
const questionCountSelect = document.getElementById("question-count");
const progressFill = document.getElementById("progress-fill");
const progressLabel = document.getElementById("progress-label");

function showToast(message) {
  toastEl.textContent = message;
  toastEl.classList.add("show");
  setTimeout(() => {
    toastEl.classList.remove("show");
  }, 2600);
}

function loadStoredUsername() {
  const stored = localStorage.getItem("quiz_username");
  if (stored) {
    usernameInput.value = stored;
  }
}

function saveUsername() {
  const value = usernameInput.value.trim();
  if (!value) {
    showToast("Please enter a username.");
    return;
  }
  localStorage.setItem("quiz_username", value);
  showToast(`Username saved as "${value}".`);
}

function difficultyLabel(difficulty) {
  switch (difficulty) {
    case 1:
      return "Easy";
    case 2:
      return "Medium";
    case 3:
      return "Hard";
    default:
      return `Level ${difficulty}`;
  }
}

function renderQuestion() {
  if (!questions.length) {
    questionTextEl.textContent = "No questions loaded.";
    optionsContainer.innerHTML = "";
    return;
  }

  const q = questions[currentQuestionIndex];
  questionCounter.textContent = `${currentQuestionIndex + 1} / ${questions.length}`;
  questionTopic.textContent = q.topic;
  questionDifficulty.textContent = difficultyLabel(q.difficulty);

  questionTextEl.textContent = q.text;

  const existingAnswer = answers.find((a) => a.question_id === q.id);
  const selectedIndex = existingAnswer ? existingAnswer.selected_index : null;

  optionsContainer.innerHTML = "";
  const letters = ["A", "B", "C", "D", "E", "F"];

  q.options.forEach((opt, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "option";
    if (selectedIndex === idx) {
      btn.classList.add("selected");
    }

    const letterSpan = document.createElement("span");
    letterSpan.className = "option-letter";
    letterSpan.textContent = letters[idx] || "?";

    const textSpan = document.createElement("span");
    textSpan.className = "option-text";
    textSpan.textContent = opt;

    btn.appendChild(letterSpan);
    btn.appendChild(textSpan);

    btn.addEventListener("click", () => {
      selectAnswer(q.id, idx);
    });

    optionsContainer.appendChild(btn);
  });

  prevBtn.disabled = currentQuestionIndex === 0;
  nextBtn.disabled = currentQuestionIndex === questions.length - 1;

  questionStartTime = performance.now();

  // Update progress
  const progress =
    questions.length > 0 ? ((currentQuestionIndex + 1) / questions.length) * 100 : 0;
  progressFill.style.width = `${progress.toFixed(0)}%`;
  progressLabel.textContent = `${progress.toFixed(0)}% complete`;
}

function selectAnswer(questionId, selectedIndex) {
  const now = performance.now();
  const timeSpent =
    questionStartTime != null ? Math.max((now - questionStartTime) / 1000, 0) : null;

  const existingIndex = answers.findIndex((a) => a.question_id === questionId);
  if (existingIndex >= 0) {
    answers[existingIndex].selected_index = selectedIndex;
    answers[existingIndex].time_spent = timeSpent;
  } else {
    answers.push({
      question_id: questionId,
      selected_index: selectedIndex,
      time_spent: timeSpent,
    });
  }

  const optionButtons = optionsContainer.querySelectorAll(".option");
  optionButtons.forEach((btn, idx) => {
    btn.classList.toggle("selected", idx === selectedIndex);
  });
}

async function fetchQuestions() {
  try {
    const topic = topicSelect.value;
    const difficulty = difficultySelect.value;
    const countValue = questionCountSelect.value;

    const params = new URLSearchParams();
    if (topic) params.append("topic", topic);
    if (difficulty) params.append("difficulty", difficulty);
    if (countValue !== "0") {
      params.append("limit", countValue);
    }

    const url =
      params.toString().length > 0
        ? `${API_BASE}/api/questions?${params.toString()}`
        : `${API_BASE}/api/questions`;

    const res = await fetch(url);
    if (!res.ok) {
      throw new Error("Failed to load questions.");
    }
    const data = await res.json();
    questions = data;
    answers = [];
    currentQuestionIndex = 0;
    submitQuizBtn.disabled = false;
    renderQuestion();
  } catch (err) {
    console.error(err);
    questionTextEl.textContent =
      "Failed to load questions from the server. Ensure the backend is running.";
    optionsContainer.innerHTML = "";
  }
}

function startQuiz() {
  const username = usernameInput.value.trim();
  if (!username) {
    showToast("Please enter and save a username first.");
    return;
  }

  fetchQuestions();
}

function goToNextQuestion() {
  if (currentQuestionIndex < questions.length - 1) {
    currentQuestionIndex += 1;
    renderQuestion();
  }
}

function goToPrevQuestion() {
  if (currentQuestionIndex > 0) {
    currentQuestionIndex -= 1;
    renderQuestion();
  }
}

function renderScore(result) {
  if (!result) {
    scoreSummaryEl.innerHTML = "<p>No quiz submitted yet.</p>";
    return;
  }

  const percent = result.score_percent.toFixed(1);
  let mood = "Keep going, every question teaches you something.";
  if (percent >= 80) {
    mood = "Awesome job! You’re crushing this topic.";
  } else if (percent >= 60) {
    mood = "Nice work! A bit more practice will push you over the top.";
  }

  scoreSummaryEl.innerHTML = `
      <div class="score-main">
        <span>${percent}</span>
        <span>%</span>
      </div>
      <div class="score-detail">
        <div>${result.correct_answers} / ${result.total_questions} correct</div>
        <div>${mood}</div>
      </div>
    `;
}

function renderPerformance(perf) {
  if (!perf || perf.total_answers === 0) {
    performanceSummaryEl.innerHTML =
      "<p>Complete at least one quiz to see your personalized performance breakdown.</p>";
    suggestionsListEl.innerHTML = "";
    (perf?.suggestions || []).forEach((s) => {
      const li = document.createElement("li");
      li.textContent = s;
      suggestionsListEl.appendChild(li);
    });
    return;
  }

  const overallPct =
    perf.overall_accuracy != null ? (perf.overall_accuracy * 100).toFixed(1) : "—";

  const list = document.createElement("ul");
  list.className = "performance-list";

  perf.topics.forEach((topic) => {
    const li = document.createElement("li");
    li.className = "performance-item";

    const topicSpan = document.createElement("span");
    topicSpan.className = "performance-topic";
    topicSpan.textContent = topic.topic;

    const bar = document.createElement("div");
    bar.className = "performance-bar";
    const barFill = document.createElement("div");
    barFill.className = "performance-bar-fill";
    barFill.style.width = `${(topic.accuracy * 100).toFixed(0)}%`;
    bar.appendChild(barFill);

    const valueSpan = document.createElement("span");
    valueSpan.style.fontSize = "0.75rem";
    valueSpan.style.color = "#9ca3af";
    valueSpan.textContent = `${(topic.accuracy * 100).toFixed(0)}%`;

    li.appendChild(topicSpan);
    li.appendChild(bar);
    li.appendChild(valueSpan);
    list.appendChild(li);
  });

  performanceSummaryEl.innerHTML = `
    <div style="font-size:0.8rem; margin-bottom:6px;">
      <strong>${perf.total_answers}</strong> answers tracked, overall accuracy
      <strong>${overallPct}%</strong>
    </div>
  `;
  performanceSummaryEl.appendChild(list);

  suggestionsListEl.innerHTML = "";
  perf.suggestions.forEach((s) => {
    const li = document.createElement("li");
    li.textContent = s;
    suggestionsListEl.appendChild(li);
  });
}

async function fetchPerformance(username) {
  try {
    const res = await fetch(
      `${API_BASE}/api/performance/${encodeURIComponent(username)}`
    );
    if (!res.ok) {
      throw new Error("Failed to load performance summary.");
    }
    const perf = await res.json();
    renderPerformance(perf);
  } catch (err) {
    console.error(err);
    performanceSummaryEl.innerHTML =
      "<p>Could not load performance data. Make sure the backend is running.</p>";
  }
}

async function submitQuiz() {
  const username = usernameInput.value.trim();
  if (!username) {
    showToast("Please enter and save a username first.");
    return;
  }

  if (!questions.length) {
    showToast("No questions loaded yet.");
    return;
  }

  const unanswered = questions.filter(
    (q) => !answers.some((a) => a.question_id === q.id)
  );

  if (unanswered.length > 0) {
    const proceed = confirm(
      `You have not answered ${unanswered.length} question(s). Submit anyway?`
    );
    if (!proceed) {
      return;
    }
  }

  const payload = {
    username,
    answers,
  };

  submitQuizBtn.disabled = true;
  submitQuizBtn.textContent = "Submitting...";

  try {
    const res = await fetch(`${API_BASE}/api/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error("Failed to submit quiz.");
    }

    const result = await res.json();
    renderScore(result);
    showToast("Quiz submitted. Loading your performance insights...");
    await fetchPerformance(username);
  } catch (err) {
    console.error(err);
    showToast("Error submitting quiz. Check console/backend logs.");
  } finally {
    submitQuizBtn.disabled = false;
    submitQuizBtn.textContent = "Submit Quiz";
  }
}

async function fetchCatalog() {
  try {
    const res = await fetch(`${API_BASE}/api/catalog`);
    if (!res.ok) {
      throw new Error("Failed to load catalog.");
    }
    const data = await res.json();

    // Populate topics
    topicSelect.innerHTML = '<option value="">All topics</option>';
    (data.topics || []).forEach((topic) => {
      const opt = document.createElement("option");
      opt.value = topic;
      opt.textContent = topic;
      topicSelect.appendChild(opt);
    });

    // Populate difficulties
    difficultySelect.innerHTML = '<option value="">All levels</option>';
    (data.difficulties || []).forEach((diff) => {
      const opt = document.createElement("option");
      opt.value = String(diff.value);
      opt.textContent = diff.label;
      difficultySelect.appendChild(opt);
    });

    // Set default question count if returned
    if (typeof data.default_limit === "number" && data.default_limit > 0) {
      const optionToSelect = Array.from(questionCountSelect.options).find(
        (o) => Number(o.value) === data.default_limit
      );
      if (optionToSelect) {
        questionCountSelect.value = String(data.default_limit);
      }
    }
  } catch (err) {
    console.error(err);
  }
}

function attachEventListeners() {
  saveUsernameBtn.addEventListener("click", saveUsername);
  startQuizBtn.addEventListener("click", startQuiz);
  nextBtn.addEventListener("click", goToNextQuestion);
  prevBtn.addEventListener("click", goToPrevQuestion);
  submitQuizBtn.addEventListener("click", submitQuiz);
}

function init() {
  loadStoredUsername();
  attachEventListeners();
   fetchCatalog();
}

document.addEventListener("DOMContentLoaded", init);

