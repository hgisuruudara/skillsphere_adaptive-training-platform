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

  document.getElementById("fairnessTable").innerHTML = m.fairness_monitor.map((f) => `
    <tr>
      <td>${f.cohort}</td>
      <td>${f.learner_count}</td>
      <td>${Math.round(f.avg_mastery * 100)}%</td>
      <td>${f.deviation_from_overall >= 0 ? "+" : ""}${Math.round(f.deviation_from_overall * 100)}%</td>
      <td>${f.flag ? '<span class="pill flag">review</span>' : '<span class="pill">ok</span>'}</td>
    </tr>
  `).join("") || '<tr><td colspan="5" class="muted">No skill data yet.</td></tr>';

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

loadMetrics();
setInterval(loadMetrics, 15000);
