const API = "";

let state = {
  learnerId: null,
  displayName: null,
  currentQuest: null,
  questStartedAt: null,
};

const $ = (id) => document.getElementById(id);

function storedLearner() {
  try {
    return JSON.parse(localStorage.getItem("skillsphere_learner") || "null");
  } catch {
    return null;
  }
}

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

// ---------- Step 1: Consent ----------
$("startBtn").addEventListener("click", async () => {
  const learnerId = $("learnerId").value.trim();
  const displayName = $("displayName").value.trim() || learnerId;
  const cohort = $("cohort").value.trim() || null;
  const consent = $("consentCheck").checked;

  if (!learnerId) { alert("Please choose a learner ID."); return; }
  if (!consent) { alert("Consent is required before training data can be collected."); return; }

  await api("/api/consent", {
    method: "POST",
    body: JSON.stringify({ learner_id: learnerId, display_name: displayName, cohort, consent }),
  });

  state.learnerId = learnerId;
  state.displayName = displayName;
  localStorage.setItem("skillsphere_learner", JSON.stringify(state));

  $("consentCard").classList.add("hidden");
  await refreshAll();
});

// ---------- Rendering ----------
async function refreshAll() {
  await Promise.all([loadProfile(), loadQuests()]);
  $("learnerCard").classList.remove("hidden");
  $("masteryCard").classList.remove("hidden");
  $("masteryTimelineCard").classList.remove("hidden");
  $("questCard").classList.remove("hidden");
}

async function loadProfile() {
  const profile = await api(`/api/learners/${encodeURIComponent(state.learnerId)}/profile`);
  $("welcomeMsg").textContent = `Welcome back, ${profile.learner.display_name}`;
  $("statPoints").textContent = profile.learner.total_points;
  $("statLevel").textContent = profile.learner.level;
  $("statBadges").textContent = profile.badges.length;

  $("badgeList").innerHTML = profile.badges
    .map((b) => `<span class="badge-chip">${b.name}</span>`)
    .join("") || '<span class="muted">No badges yet - complete a quest to earn your first one.</span>';

  const skills = profile.skills.length
    ? profile.skills
    : [];
  $("masteryList").innerHTML = skills.length
    ? skills.map(skillCard).join("")
    : '<p class="muted">No attempts yet. Mastery estimates appear after your first quest.</p>';

  renderMasteryChart(profile.mastery_timeline);
}

const MASTERY_CHART_COLORS = ["#4fd1c5", "#7c9cff", "#ff9f6b", "#f7d774", "#ff8fc7"];

function renderMasteryChart(timeline) {
  const container = $("masteryChart");
  if (!timeline || !timeline.length) {
    container.innerHTML = '<p class="muted">No attempts yet - a mastery growth curve appears here after your first quest.</p>';
    return;
  }

  const bySkill = {};
  timeline.forEach((p) => {
    (bySkill[p.skill] ||= []).push(p.mastery_score_after ?? 0);
  });

  const width = 320, height = 130, pad = 8;
  const lines = Object.entries(bySkill).map(([skill, scores], i) => {
    const color = MASTERY_CHART_COLORS[i % MASTERY_CHART_COLORS.length];
    const coords = scores.map((s, idx) => {
      const x = scores.length > 1 ? pad + (idx / (scores.length - 1)) * (width - 2 * pad) : width / 2;
      const y = pad + (1 - Math.max(0, Math.min(1, s))) * (height - 2 * pad);
      return [x, y];
    });
    const points = coords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
    const dots = coords.map(([x, y]) => `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.5" fill="${color}" />`).join("");
    return { skill, color, points, dots };
  });

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" class="mastery-chart-svg" preserveAspectRatio="none">
      ${lines.map((l) => `<polyline points="${l.points}" fill="none" stroke="${l.color}" stroke-width="2" />${l.dots}`).join("")}
    </svg>
    <div class="mastery-chart-legend">
      ${lines.map((l) => `<span class="legend-item"><span class="legend-dot" style="background:${l.color}"></span>${prettySkill(l.skill)}</span>`).join("")}
    </div>`;
}

function skillCard(s) {
  const pct = Math.round(s.mastery_score * 100);
  return `
    <div class="stat">
      <div class="label">${prettySkill(s.skill)}</div>
      <div class="value">${pct}%</div>
      <div class="muted">${s.attempts_count} attempts &middot; streak ${s.correct_streak}</div>
    </div>`;
}

function prettySkill(skill) {
  return skill.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

async function loadQuests() {
  const quests = await api(`/api/quests?learner_id=${encodeURIComponent(state.learnerId)}`);
  $("questList").innerHTML = quests.map((q) => `
    <div class="card" style="margin-bottom:0;">
      <h3>${prettySkill(q.skill)} &middot; Difficulty ${q.difficulty}/5</h3>
      <p>${q.prompt}</p>
      <button onclick="startQuest('${q.id}')">Start Quest</button>
    </div>
  `).join("");
}

window.startQuest = async function (questId) {
  const quests = await api(`/api/quests?learner_id=${encodeURIComponent(state.learnerId)}`);
  const quest = quests.find((q) => q.id === questId);
  openPlayCard(quest);
};

function openPlayCard(quest) {
  state.currentQuest = quest;
  state.questStartedAt = Date.now();

  $("questCard").classList.add("hidden");
  $("playCard").classList.remove("hidden");
  $("playModule").textContent = `${prettySkill(quest.skill)} - Difficulty ${quest.difficulty}/5${quest.generated_by_ai ? " (AI-generated)" : ""}`;
  $("playPrompt").textContent = quest.prompt;
  $("feedbackBox").classList.add("hidden");
  $("nextBtn").classList.add("hidden");

  $("playOptions").innerHTML = quest.options
    .map((opt, i) => `<button class="quest-option" data-idx="${i}" onclick="answerQuest(${i})">${opt}</button>`)
    .join("");
}

window.answerQuest = async function (selectedIndex) {
  document.querySelectorAll(".quest-option").forEach((b) => (b.disabled = true));
  const responseTimeMs = Date.now() - state.questStartedAt;

  const result = await api("/api/attempts", {
    method: "POST",
    body: JSON.stringify({
      learner_id: state.learnerId,
      quest_id: state.currentQuest.id,
      selected_index: selectedIndex,
      response_time_ms: responseTimeMs,
    }),
  });

  const chosenBtn = document.querySelector(`.quest-option[data-idx="${selectedIndex}"]`);
  chosenBtn.classList.add(result.correct ? "correct" : "incorrect");

  const box = $("feedbackBox");
  box.classList.remove("hidden");
  const levelUpMsg = result.level_up ? ` 🎉 Level up! You're now level ${result.level}.` : "";
  const badgeMsg = result.new_badges.length ? ` New badge(s): ${result.new_badges.join(", ")}.` : "";
  box.innerHTML = `
    <strong>${result.correct ? "Correct" : "Not quite"}</strong> · +${result.points_awarded} pts${levelUpMsg}${badgeMsg}
    <p style="margin-bottom:0;">${result.ai_feedback}</p>
  `;
  $("nextBtn").classList.remove("hidden");
};

$("nextBtn").addEventListener("click", async () => {
  $("playCard").classList.add("hidden");
  await refreshAll();
});

$("generateBtn").addEventListener("click", async () => {
  if (!state.learnerId) return;
  $("generateBtn").disabled = true;
  try {
    const quest = await api("/api/quests/generate", {
      method: "POST",
      body: JSON.stringify({ learner_id: state.learnerId, skill: "data_privacy" }),
    });
    openPlayCard(quest);
  } finally {
    $("generateBtn").disabled = false;
  }
});

// ---------- Resume session ----------
(function init() {
  const saved = storedLearner();
  if (saved && saved.learnerId) {
    state = saved;
    $("consentCard").classList.add("hidden");
    refreshAll().catch((err) => {
      // Consent may have been revoked/erased server-side; fall back to signup.
      localStorage.removeItem("skillsphere_learner");
      $("consentCard").classList.remove("hidden");
      console.warn(err);
    });
  }
})();
