async function loadMetrics() {
  const res = await fetch("/api/dashboard/metrics");
  const m = await res.json();

  document.getElementById("statRow").innerHTML = [
    ["Total Learners", m.total_learners],
    ["Consented", m.consented_learners],
    ["Total Attempts", m.total_attempts],
    ["Overall Accuracy", `${Math.round(m.overall_accuracy * 100)}%`],
    ["Avg Response Time", `${Math.round(m.avg_response_time_ms)} ms`],
    ["Active (7d)", m.active_last_7_days],
  ].map(([label, value]) => `
    <div class="stat"><div class="value">${value}</div><div class="label">${label}</div></div>
  `).join("");

  const maxAttempts = Math.max(1, ...m.engagement_by_day.map((d) => d.attempts));
  document.getElementById("engagementChart").innerHTML = m.engagement_by_day
    .map((d) => `<div class="bar" style="height:${Math.max(2, (d.attempts / maxAttempts) * 100)}%" title="${d.date}: ${d.attempts} completions"></div>`)
    .join("");
  document.getElementById("engagementLegend").textContent =
    `${m.engagement_by_day[0]?.date || ""} → ${m.engagement_by_day.at(-1)?.date || ""} (bar height = quest completions/day)`;

  // The flag is computed server-side on the unrounded deviation against a
  // 15-point threshold, so rounding the column to whole points made a 14.7
  // deviation read as "+15%" beside an "ok" pill - the number appeared to
  // contradict the rule printed under the table. One decimal place keeps the
  // displayed value on the same side of the threshold as the decision.
  document.getElementById("fairnessTable").innerHTML = m.fairness_monitor.map((f) => `
    <tr>
      <td>${f.cohort}</td>
      <td>${f.learner_count}</td>
      <td>${(f.avg_mastery * 100).toFixed(1)}%</td>
      <td>${f.deviation_from_overall >= 0 ? "+" : ""}${(f.deviation_from_overall * 100).toFixed(1)}%</td>
      <td>${f.p_value === null || f.p_value === undefined ? "n/a" : f.p_value.toFixed(4)}</td>
      <td>${f.flag ? '<span class="pill flag">review</span>' : '<span class="pill">ok</span>'}</td>
    </tr>
  `).join("") || '<tr><td colspan="6" class="muted">No skill data yet.</td></tr>';

  document.getElementById("leaderboardTable").innerHTML = m.top_learners.map((l, i) => `
    <tr><td>${i + 1}</td><td>${l.display_name}</td><td>${l.level}</td><td>${l.points}</td></tr>
  `).join("") || '<tr><td colspan="4" class="muted">No learners yet.</td></tr>';

  const tc = m.technique_comparison;
  document.getElementById("techniqueRow").innerHTML = tc.sample_size
    ? [
        ["Sample Size", tc.sample_size],
        ["Avg EMA Mastery", `${Math.round(tc.avg_ema_mastery * 100)}%`],
        ["Avg BKT Mastery", `${Math.round(tc.avg_bkt_mastery * 100)}%`],
        ["Mean Abs. Difference", `${Math.round(tc.mean_absolute_difference * 100)}%`],
        ["Agreement Rate", `${Math.round(tc.agreement_rate * 100)}%`],
      ].map(([label, value]) => `
        <div class="stat"><div class="value">${value}</div><div class="label">${label}</div></div>
      `).join("")
    : '<p class="muted">No attempts yet - comparison appears once learners start answering quests.</p>';
}

// R3 evidence. The endpoint existed and was tested from the start, but nothing
// rendered it, so the comparative study could only be read by calling the API
// directly. This panel puts the same figures where an instructor can see them.
const CONDITION_LABELS = {
  treatment: "Adaptive (AI-driven)",
  control: "Non-adaptive (traditional)",
};

function pct(value) {
  return value === null || value === undefined ? "-" : `${(value * 100).toFixed(1)}%`;
}

function num(value, digits = 4) {
  return value === null || value === undefined ? "-" : value.toFixed(digits);
}

async function loadComparison() {
  const c = await (await fetch("/api/dashboard/comparison")).json();

  document.getElementById("comparisonTable").innerHTML = ["treatment", "control"]
    .map((key) => {
      const row = c[key];
      return `
        <tr>
          <td>${CONDITION_LABELS[key]}</td>
          <td>${row.learner_count}</td>
          <td>${num(row.avg_mastery_growth_rate)}</td>
          <td>${pct(row.overall_accuracy)}</td>
          <td>${row.avg_attempts_per_learner === null ? "-" : row.avg_attempts_per_learner}</td>
        </tr>`;
    }).join("");

  // Cohen's d is null until both arms have at least two learners with
  // attempts; say so rather than rendering an empty tile.
  document.getElementById("effectSizeRow").innerHTML = c.cohens_d === null
    ? ""
    : [
        ["Cohen's d", num(c.cohens_d, 3)],
        ["Effect Size", c.effect_size_interpretation],
      ].map(([label, value]) => `
        <div class="stat"><div class="value">${value}</div><div class="label">${label}</div></div>
      `).join("");

  document.getElementById("comparisonNote").textContent = c.cohens_d === null
    ? "Effect size requires at least two learners with attempts in each condition - not yet available."
    : c.note;
}

function refresh() {
  loadMetrics();
  loadComparison();
}

refresh();
setInterval(refresh, 15000);
