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

function generateLearnerId() {
  const bytes = new Uint8Array(6);
  crypto.getRandomValues(bytes);
  const code = Array.from(bytes, (b) => b.toString(36)).join("").slice(0, 8).toUpperCase();
  return `L-${code}`;
}

// Shows a blank registration form with a freshly auto-generated learner ID -
// used both on first visit and when switching to a new user.
function showRegistration() {
  localStorage.removeItem("skillsphere_learner");
  state = { learnerId: null, displayName: null, currentQuest: null, questStartedAt: null };

  ["learnerCard", "masteryCard", "masteryTimelineCard", "questCard", "playCard"]
    .forEach((id) => $(id).classList.add("hidden"));

  $("learnerId").value = generateLearnerId();
  $("displayName").value = "";
  $("cohort").value = "";
  $("consentCheck").checked = false;
  $("resumeBox").classList.add("hidden");
  $("resumeId").value = "";
  $("resumeMsg").textContent = "";
  $("consentCard").classList.remove("hidden");
}

$("newUserLink").addEventListener("click", (event) => {
  event.preventDefault();
  showRegistration();
});

// ---------- Resume on a new browser/device with an existing learner ID ----------
$("showResumeLink").addEventListener("click", (event) => {
  event.preventDefault();
  $("resumeBox").classList.toggle("hidden");
});

$("resumeBtn").addEventListener("click", () => {
  const id = $("resumeId").value.trim();
  if (!id) { $("resumeMsg").textContent = "Enter a learner ID first."; return; }
  attemptResume(id);
});

async function attemptResume(id) {
  $("resumeMsg").textContent = "";
  $("resumeBtn").disabled = true;
  try {
    const profile = await api(`/api/learners/${encodeURIComponent(id)}/profile`);
    state = { learnerId: id, displayName: profile.learner.display_name, currentQuest: null, questStartedAt: null };
    try {
      await refreshAll();
      localStorage.setItem("skillsphere_learner", JSON.stringify(state));
      $("consentCard").classList.add("hidden");
      $("resumeBox").classList.add("hidden");
    } catch {
      // Profile exists, but a data-writing call (e.g. quests) came back 403 -
      // consent isn't currently active for this ID (never granted, withdrawn,
      // or erased). Let the learner re-consent under the same ID rather than
      // silently starting a brand new one.
      $("learnerId").value = id;
      $("displayName").value = profile.learner.display_name || "";
      $("resumeMsg").textContent = "This ID exists, but consent isn't currently active - re-consent below with the same ID to continue.";
    }
  } catch {
    $("resumeMsg").textContent = "No learner found with that ID. Check it and try again.";
  } finally {
    $("resumeBtn").disabled = false;
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
  $("learnerIdLine").textContent = `Learner ID: ${profile.learner.id}`;
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

// Matched against Badge.name from evaluate_badges() in gamification/engine.py -
// a default icon covers any future badge added there without a matching update here.
const BADGE_ICONS = {
  "First Steps": "👣",
  "Quick Learner (3-streak)": "⚡",
  "Perfectionist (5-streak)": "🌟",
  "Skill Master": "🏆",
  "Consistent Learner": "📅",
};
const DEFAULT_BADGE_ICON = "🎖️";

function showRewardToast({ type, icon, title, name }) {
  const container = $("rewardToasts");
  const toast = document.createElement("div");
  toast.className = `reward-toast ${type}`;
  toast.innerHTML = `
    <div class="reward-icon">${icon}</div>
    <div class="reward-text">
      <div class="reward-title">${title}</div>
      <div class="reward-name">${name}</div>
    </div>`;
  toast.addEventListener("animationend", (event) => {
    if (event.animationName === "reward-toast-out") toast.remove();
  });
  container.appendChild(toast);
}

// Re-triggers the pulse animation even if the tile already pulsed recently -
// removing then reflowing then re-adding the class restarts a CSS animation
// that a plain re-add would otherwise skip (same class already applied).
function pulseStat(id) {
  const el = $(id);
  el.classList.remove("stat-pulse");
  void el.offsetWidth;
  el.classList.add("stat-pulse");
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
  box.innerHTML = `
    <strong>${result.correct ? "Correct" : "Not quite"}</strong> · +${result.points_awarded} pts
    <p style="margin-bottom:0;">${result.ai_feedback}</p>
  `;

  // Update the KPI tiles the instant the result comes back, rather than
  // leaving them stale until "Back to quests" triggers a full refreshAll().
  $("statPoints").textContent = result.total_points;
  if (result.points_awarded > 0) pulseStat("statPoints");

  $("statLevel").textContent = result.level;
  if (result.level_up) pulseStat("statLevel");

  if (result.new_badges.length) {
    const currentBadgeCount = parseInt($("statBadges").textContent, 10) || 0;
    $("statBadges").textContent = currentBadgeCount + result.new_badges.length;
    pulseStat("statBadges");

    const placeholder = $("badgeList").querySelector(".muted");
    if (placeholder) $("badgeList").innerHTML = "";
    result.new_badges.forEach((name) => {
      $("badgeList").insertAdjacentHTML("beforeend", `<span class="badge-chip">${name}</span>`);
    });
  }

  // Celebrate level-ups and new badges as animated toasts rather than plain
  // text - staggered slightly so multiple rewards from one attempt (e.g. a
  // level-up and a streak badge together) don't all pop in at once.
  let delay = 0;
  if (result.level_up) {
    showRewardToast({ type: "levelup", icon: "🎉", title: "Level Up", name: `You're now level ${result.level}` });
    delay += 350;
  }
  result.new_badges.forEach((name) => {
    setTimeout(() => showRewardToast({
      type: "badge", icon: BADGE_ICONS[name] || DEFAULT_BADGE_ICON, title: "Badge Earned", name,
    }), delay);
    delay += 350;
  });
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
      showRegistration();
      console.warn(err);
    });
  } else {
    $("learnerId").value = generateLearnerId();
  }
})();
