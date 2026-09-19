const API = (window.SNAPSELL_API || "").replace(/\/$/, "");
const $ = (sel) => document.querySelector(sel);

let password = sessionStorage.getItem("snapsell_admin") || "";

const SYMBOLS = { INR: "₹", USD: "$", EUR: "€" };

function money(minor, currency) {
  const amount = (minor || 0) / 100;
  const symbol = SYMBOLS[currency] || `${currency} `;
  return symbol + amount.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function escapeHtml(text) {
  return String(text).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

function when(value) {
  const date = new Date(String(value).replace(" ", "T") + "Z");
  return isNaN(date) ? value : date.toLocaleString();
}

async function fetchStats() {
  const res = await fetch(`${API}/api/admin/stats`, { headers: { "X-Admin-Password": password } });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function table(node, columns, rows, renderRow) {
  const head = `<tr>${columns.map((c) => `<th>${c}</th>`).join("")}</tr>`;
  const body = rows.length
    ? rows.map(renderRow).join("")
    : `<tr><td class="empty" colspan="${columns.length}">Nothing yet</td></tr>`;
  node.innerHTML = head + body;
}

function render(stats) {
  const paidTotals = stats.revenue.map((r) => money(r.minor, r.currency)).join(" + ") || "—";
  const todayTotals = stats.revenue_today.map((r) => money(r.minor, r.currency)).join(" + ") || "—";
  const runs = stats.tools.reduce((sum, t) => sum + t.runs, 0);

  $("#kpis").innerHTML = [
    ["Revenue today", todayTotals],
    ["Revenue all time", paidTotals],
    ["Users", stats.users.total],
    ["New this week", stats.users.week],
    ["Tool runs", runs],
    ["Credits outstanding", stats.credits_outstanding],
    ["Gateway", stats.provider === "none" ? "not configured" : stats.provider],
    ["AI model", stats.ai ? "live" : "demo mode"],
  ]
    .map(([label, value]) => `<div class="card"><div class="value">${escapeHtml(value)}</div><div class="label">${label}</div></div>`)
    .join("");

  table($("#revenue"), ["Currency", "Paid orders", "Gross", "Credits sold"], stats.revenue, (r) =>
    `<tr><td>${escapeHtml(r.currency)}</td><td>${r.orders}</td><td>${money(r.minor, r.currency)}</td><td>${r.credits}</td></tr>`);

  table($("#tools"), ["Tool", "Runs", "Credits used"], stats.tools, (t) =>
    `<tr><td>${escapeHtml(t.tool)}</td><td>${t.runs}</td><td>${t.credits}</td></tr>`);

  table($("#orders"), ["When", "Email", "Pack", "Amount", "Status"], stats.orders, (o) =>
    `<tr><td>${when(o.created_at)}</td><td>${escapeHtml(o.email)}</td><td>${escapeHtml(o.pack_id)}</td>` +
    `<td>${money(o.amount_minor, o.currency)}</td><td class="tag-${escapeHtml(o.status)}">${escapeHtml(o.status)}</td></tr>`);

  table($("#signups"), ["When", "Email", "Credits"], stats.signups, (u) =>
    `<tr><td>${when(u.created_at)}</td><td>${escapeHtml(u.email)}</td><td>${u.credits}</td></tr>`);
}

async function load() {
  const stats = await fetchStats();
  render(stats);
  $("#gate").classList.add("hidden");
  $("#board").classList.remove("hidden");
  $("#signout").classList.remove("hidden");
}

$("#gate").addEventListener("submit", async (event) => {
  event.preventDefault();
  password = $("#password").value;
  try {
    await load();
    sessionStorage.setItem("snapsell_admin", password);
  } catch (err) {
    const error = $("#gate-error");
    error.textContent = err.message;
    error.classList.remove("hidden");
  }
});

$("#signout").addEventListener("click", () => {
  sessionStorage.removeItem("snapsell_admin");
  location.reload();
});

if (password) {
  load().catch(() => sessionStorage.removeItem("snapsell_admin"));
}
