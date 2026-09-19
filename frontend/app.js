const API = (window.SNAPSELL_API || "").replace(/\/$/, "");
const state = {
  token: localStorage.getItem("snapsell_token") || null,
  user: null,
  catalog: null,
  tool: null,
  mode: "signup",
  pendingPack: null,
};

const $ = (sel) => document.querySelector(sel);

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(API + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function escapeHtml(text) {
  return text.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

function renderMarkdown(text) {
  return escapeHtml(text)
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^# (.*)$/gm, "<h2>$1</h2>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/^[-*] (.*)$/gm, "• $1");
}

function money(minor, currency) {
  const symbol = currency === "INR" ? "₹" : "$";
  return symbol + (minor / 100).toLocaleString(undefined, { maximumFractionDigits: 2 });
}

// ------------------------------------------------------------------ rendering

function renderTools() {
  $("#tool-grid").innerHTML = state.catalog.tools
    .map(
      (tool) => `
      <div class="card tool-card" data-tool="${tool.id}">
        <h3>${tool.name}</h3>
        <p>${tool.blurb}</p>
        <span class="cost">${tool.cost} credit${tool.cost > 1 ? "s" : ""} per run</span>
      </div>`
    )
    .join("");
  document.querySelectorAll(".tool-card").forEach((card) =>
    card.addEventListener("click", () => openTool(card.dataset.tool))
  );
}

function renderPacks() {
  const inr = state.catalog.provider === "razorpay";
  $("#pack-grid").innerHTML = state.catalog.packs
    .map(
      (pack) => `
      <div class="card pack ${pack.popular ? "popular" : ""}">
        ${pack.popular ? '<span class="badge">Most popular</span>' : ""}
        <h3>${pack.name}</h3>
        <div class="price">${money(inr ? pack.inr : pack.usd, inr ? "INR" : "USD")}</div>
        <div class="credits">${pack.credits} credits</div>
        <p>${pack.blurb}</p>
        <button class="btn btn-primary" data-pack="${pack.id}">Buy credits</button>
      </div>`
    )
    .join("");
  document.querySelectorAll("[data-pack]").forEach((btn) =>
    btn.addEventListener("click", () => buy(btn.dataset.pack))
  );
  const note = {
    razorpay: "Payments processed by Razorpay (UPI, cards, netbanking). Credits land instantly.",
    stripe: "Payments processed by Stripe. Credits land instantly after checkout.",
    none: "Checkout is not live yet — connect a payment gateway to enable purchases.",
  }[state.catalog.provider];
  $("#provider-note").textContent = note;
}

function renderUser() {
  const pill = $("#credit-pill");
  if (state.user) {
    pill.textContent = `${state.user.credits} credits`;
    pill.classList.remove("hidden");
    $("#nav-auth").textContent = "Sign out";
  } else {
    pill.classList.add("hidden");
    $("#nav-auth").textContent = "Sign in";
  }
}

function openTool(toolId) {
  if (!state.user) return openModal("signup");
  state.tool = state.catalog.tools.find((t) => t.id === toolId);
  $("#workspace").classList.remove("hidden");
  $("#workspace-title").textContent = state.tool.name;
  $("#tool-form").innerHTML =
    state.tool.inputs
      .map((field) =>
        field.type === "textarea"
          ? `<label>${field.label}<textarea name="${field.key}" placeholder="${field.placeholder}"></textarea></label>`
          : `<label>${field.label}<input name="${field.key}" placeholder="${field.placeholder}" /></label>`
      )
      .join("") +
    `<button class="btn btn-primary btn-block" type="submit">Run · ${state.tool.cost} credit${
      state.tool.cost > 1 ? "s" : ""
    }</button>`;
  $("#output").innerHTML = '<p class="muted">Fill the form and run the tool.</p>';
  $("#workspace").scrollIntoView({ behavior: "smooth" });
}

// ------------------------------------------------------------------ actions

async function runTool(event) {
  event.preventDefault();
  const form = event.target;
  const button = form.querySelector("button");
  const payload = Object.fromEntries(new FormData(form).entries());
  button.disabled = true;
  button.textContent = "Thinking…";
  $("#output").innerHTML = '<p class="muted">Generating…</p>';
  try {
    const data = await api(`/api/tools/${state.tool.id}`, { method: "POST", body: { payload } });
    $("#output").innerHTML = `<pre>${renderMarkdown(data.output)}</pre>`;
    state.user.credits = data.credits;
    renderUser();
  } catch (err) {
    $("#output").innerHTML = `<p class="error">${escapeHtml(err.message)}</p>`;
    if (/credits/i.test(err.message)) document.querySelector("#pricing").scrollIntoView({ behavior: "smooth" });
  } finally {
    button.disabled = false;
    button.textContent = `Run · ${state.tool.cost} credit${state.tool.cost > 1 ? "s" : ""}`;
  }
}

async function buy(packId) {
  if (!state.user) {
    state.pendingPack = packId;
    return openModal("signup");
  }
  try {
    const session = await api("/api/checkout", { method: "POST", body: { pack_id: packId } });
    if (session.provider === "stripe") {
      window.location.href = session.url;
      return;
    }
    const rzp = new window.Razorpay({
      key: session.key_id,
      order_id: session.order_id,
      amount: session.amount,
      currency: session.currency,
      name: "SnapSell",
      description: session.name,
      prefill: { email: state.user.email },
      theme: { color: "#ffd166" },
      handler: async (response) => {
        const result = await api("/api/payments/razorpay/verify", {
          method: "POST",
          body: response,
        });
        state.user.credits = result.credits;
        renderUser();
        alert(`Payment received. You now have ${result.credits} credits.`);
      },
    });
    rzp.open();
  } catch (err) {
    alert(err.message);
  }
}

function openModal(mode) {
  state.mode = mode;
  const signup = mode === "signup";
  $("#auth-title").textContent = signup ? "Create your account" : "Welcome back";
  $("#auth-sub").innerHTML = signup
    ? `Get <span class="free-credits">${state.catalog?.free_credits ?? 5}</span> free credits. No card needed.`
    : "Sign in to use your credits.";
  $("#auth-submit").textContent = signup ? "Create account" : "Sign in";
  $("#auth-switch").textContent = signup ? "Sign in" : "Create one";
  $("#auth-switch").previousSibling.textContent = signup
    ? "Already have an account? "
    : "No account yet? ";
  $("#auth-error").classList.add("hidden");
  $("#modal").classList.remove("hidden");
}

async function submitAuth(event) {
  event.preventDefault();
  const form = event.target;
  const body = Object.fromEntries(new FormData(form).entries());
  const button = $("#auth-submit");
  button.disabled = true;
  try {
    const data = await api(`/api/auth/${state.mode}`, { method: "POST", body });
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem("snapsell_token", data.token);
    $("#modal").classList.add("hidden");
    form.reset();
    renderUser();
    if (state.pendingPack) {
      const pack = state.pendingPack;
      state.pendingPack = null;
      buy(pack);
    }
  } catch (err) {
    const box = $("#auth-error");
    box.textContent = err.message;
    box.classList.remove("hidden");
  } finally {
    button.disabled = false;
  }
}

function signOut() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("snapsell_token");
  $("#workspace").classList.add("hidden");
  renderUser();
}

// ------------------------------------------------------------------ boot

async function boot() {
  state.catalog = await api("/api/catalog");
  $("#free-credits").textContent = state.catalog.free_credits;
  document.querySelectorAll(".free-credits").forEach((el) => {
    el.textContent = state.catalog.free_credits;
  });
  renderTools();
  renderPacks();
  if (state.token) {
    try {
      const data = await api("/api/me");
      state.user = data.user;
    } catch {
      signOut();
    }
  }
  renderUser();
}

$("#nav-auth").addEventListener("click", () => (state.user ? signOut() : openModal("login")));
$("#hero-cta").addEventListener("click", () =>
  state.user ? openTool(state.catalog.tools[0].id) : openModal("signup")
);
$("#modal-close").addEventListener("click", () => $("#modal").classList.add("hidden"));
$("#auth-switch").addEventListener("click", (e) => {
  e.preventDefault();
  openModal(state.mode === "signup" ? "login" : "signup");
});
$("#auth-form").addEventListener("submit", submitAuth);
$("#tool-form").addEventListener("submit", runTool);

boot().catch((err) => {
  document.querySelector("#tool-grid").innerHTML = `<p class="error">Could not reach the API: ${err.message}</p>`;
});
