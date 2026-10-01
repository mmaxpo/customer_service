(() => {
  const SCRIPT_ID = "tajeran-chat-widget-script";
  const ROOT_ID = "tajeran-chat-widget-root";
  const VERSION = "0.1.0";

  const currentScript =
    document.currentScript ||
    document.querySelector(`script[src*="tajeran-chat-widget.js"]`) ||
    document.getElementById(SCRIPT_ID);

  if (!currentScript) return;

  const publicKey = currentScript.getAttribute("data-tajeran-public-key");
  if (!publicKey) {
    console.warn("[Tajeran Chat] Missing data-tajeran-public-key.");
    return;
  }

  if (document.getElementById(ROOT_ID)) return;

  const scriptUrl = new URL(currentScript.src, window.location.href);
  const apiBase =
    currentScript.getAttribute("data-tajeran-api-base") ||
    `${scriptUrl.origin}/api/customer-service/chat/public/${publicKey}`;

  const storagePrefix = `tajeran_chat_${publicKey}`;
  const visitorKey = `${storagePrefix}_visitor_id`;
  const sessionKey = `${storagePrefix}_session_id`;
  const customerName =
    currentScript.getAttribute("data-tajeran-customer-name") ||
    window.TajeranChatCustomer?.name ||
    null;

  const customerEmail =
    currentScript.getAttribute("data-tajeran-customer-email") ||
    window.TajeranChatCustomer?.email ||
    null;


  const ratedKey = `${storagePrefix}_rated_session`;

  const state = {
    settings: null,
    visitorId: getOrCreateVisitorId(),
    sessionId: localStorage.getItem(sessionKey),
    messages: [],
    open: false,
    loading: false,
    sending: false,
    pollTimer: null,
    ratedSessionId: localStorage.getItem(ratedKey),
    // Self-service: the open form ({ kind, busy, error }) and answers shown
    // only in this chat window (order status is not saved to the conversation).
    selfService: null,
    notes: [],
  };

  const SELF_SERVICE = {
    track_order: { label: "Track my order", submit: "Check status" },
    report_problem: { label: "Report a problem", submit: "Send to our team", prompt: "What went wrong?" },
    start_return: { label: "Start a return", submit: "Send to our team", prompt: "Why are you returning it?" },
  };

  const root = document.createElement("div");
  root.id = ROOT_ID;
  root.setAttribute("data-version", VERSION);
  document.body.appendChild(root);

  const style = document.createElement("style");
  style.textContent = `
    #${ROOT_ID}, #${ROOT_ID} * {
      box-sizing: border-box;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    #${ROOT_ID} .tj-widget {
      position: fixed;
      z-index: 2147483647;
      bottom: 22px;
    }

    #${ROOT_ID} .tj-widget.tj-right { right: 22px; }
    #${ROOT_ID} .tj-widget.tj-left { left: 22px; }

    #${ROOT_ID} .tj-panel {
      width: min(360px, calc(100vw - 32px));
      height: min(560px, calc(100vh - 110px));
      margin-bottom: 14px;
      overflow: hidden;
      border: 1px solid rgba(15, 23, 42, 0.12);
      border-radius: 24px;
      background: #ffffff;
      box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
      display: none;
    }

    #${ROOT_ID} .tj-panel.tj-open {
      display: flex;
      flex-direction: column;
    }

    #${ROOT_ID} .tj-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      color: #ffffff;
    }

    #${ROOT_ID} .tj-avatar {
      width: 38px;
      height: 38px;
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.18);
      font-weight: 800;
      flex: none;
    }

    #${ROOT_ID} .tj-title {
      font-size: 14px;
      font-weight: 800;
      line-height: 1.2;
    }

    #${ROOT_ID} .tj-subtitle {
      margin-top: 2px;
      font-size: 12px;
      opacity: 0.86;
    }

    #${ROOT_ID} .tj-close {
      margin-left: auto;
      border: 0;
      background: rgba(255, 255, 255, 0.16);
      color: #ffffff;
      width: 32px;
      height: 32px;
      border-radius: 999px;
      cursor: pointer;
      font-size: 18px;
      line-height: 1;
    }

    #${ROOT_ID} .tj-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    }

    #${ROOT_ID} .tj-bubble {
      max-width: 82%;
      margin-bottom: 10px;
      padding: 10px 12px;
      border-radius: 18px;
      font-size: 14px;
      line-height: 1.45;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }

    #${ROOT_ID} .tj-bubble-assistant {
      margin-right: auto;
      border-bottom-left-radius: 6px;
      background: #eef2f7;
      color: #0f172a;
    }

    #${ROOT_ID} .tj-bubble-customer {
      margin-left: auto;
      border-bottom-right-radius: 6px;
      background: #0f172a;
      color: #ffffff;
    }

    #${ROOT_ID} .tj-empty {
      color: #64748b;
      font-size: 13px;
      line-height: 1.55;
    }

    #${ROOT_ID} .tj-input-row {
      display: flex;
      gap: 8px;
      border-top: 1px solid #e2e8f0;
      padding: 12px;
      background: #ffffff;
    }

    #${ROOT_ID} .tj-input {
      min-width: 0;
      flex: 1;
      border: 1px solid #cbd5e1;
      border-radius: 16px;
      padding: 11px 12px;
      font-size: 14px;
      outline: none;
    }

    #${ROOT_ID} .tj-input:focus {
      border-color: #0f172a;
      box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.08);
    }

    #${ROOT_ID} .tj-send {
      border: 0;
      border-radius: 16px;
      color: #ffffff;
      cursor: pointer;
      font-weight: 800;
      padding: 0 14px;
      min-width: 58px;
    }

    #${ROOT_ID} .tj-send:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }

    #${ROOT_ID} .tj-launcher {
      width: 60px;
      height: 60px;
      border: 0;
      border-radius: 999px;
      color: #ffffff;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 18px 45px rgba(15, 23, 42, 0.28);
    }

    #${ROOT_ID} .tj-launcher svg {
      width: 26px;
      height: 26px;
    }

    #${ROOT_ID} .tj-error {
      margin: 12px;
      border-radius: 14px;
      background: #fef2f2;
      color: #991b1b;
      padding: 10px 12px;
      font-size: 12px;
      line-height: 1.45;
    }

    #${ROOT_ID} .tj-feedback {
      display: flex;
      align-items: center;
      gap: 4px;
      margin: -4px 0 12px;
      color: #64748b;
      font-size: 12px;
    }

    #${ROOT_ID} .tj-feedback button,
    #${ROOT_ID} .tj-rating button {
      min-width: 32px;
      height: 32px;
      border: 1px solid #e2e8f0;
      border-radius: 999px;
      background: #ffffff;
      color: #0f172a;
      cursor: pointer;
      font-size: 13px;
    }

    #${ROOT_ID} .tj-feedback button:hover,
    #${ROOT_ID} .tj-rating button:hover {
      border-color: #94a3b8;
    }

    #${ROOT_ID} .tj-rating {
      display: flex;
      align-items: center;
      gap: 6px;
      border-top: 1px solid #e2e8f0;
      padding: 10px 12px 0;
      color: #334155;
      font-size: 12.5px;
      background: #ffffff;
    }

    #${ROOT_ID} .tj-rating span { margin-right: auto; }

    #${ROOT_ID} .tj-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      border-top: 1px solid #e2e8f0;
      padding: 10px 12px 0;
      background: #ffffff;
    }

    #${ROOT_ID} .tj-actions button,
    #${ROOT_ID} .tj-cancel {
      border: 1px solid #cbd5e1;
      border-radius: 999px;
      background: #ffffff;
      color: #0f172a;
      cursor: pointer;
      font-size: 12.5px;
      padding: 7px 11px;
    }

    #${ROOT_ID} .tj-actions button:hover,
    #${ROOT_ID} .tj-cancel:hover {
      border-color: #94a3b8;
    }

    #${ROOT_ID} .tj-form {
      display: grid;
      gap: 8px;
      border-top: 1px solid #e2e8f0;
      padding: 12px;
      background: #ffffff;
    }

    #${ROOT_ID} .tj-form-title {
      font-size: 13px;
      font-weight: 800;
      color: #0f172a;
    }

    #${ROOT_ID} .tj-form textarea.tj-input {
      resize: none;
      font-family: inherit;
    }

    #${ROOT_ID} .tj-form-buttons {
      display: flex;
      gap: 8px;
    }

    #${ROOT_ID} .tj-form-buttons .tj-send {
      flex: 1;
      height: 38px;
    }

    #${ROOT_ID} .tj-form-error {
      color: #991b1b;
      font-size: 12px;
    }

    #${ROOT_ID} .tj-bubble a {
      color: inherit;
      font-weight: 700;
    }

    #${ROOT_ID} .tj-powered {
      padding: 8px 12px 10px;
      text-align: center;
      color: #94a3b8;
      font-size: 11px;
      background: #ffffff;
    }

    #${ROOT_ID} .tj-powered strong {
      color: #475569;
    }
  `;
  document.head.appendChild(style);

  boot();

  async function boot() {
    renderShell();

    try {
      state.loading = true;
      const settings = await fetchJson(`${apiBase}/settings`);
      if (!settings.enabled) return;
      state.settings = settings;

      renderShell();
      await ensureSession();
      await loadMessages();
      startPolling();
    } catch (error) {
      console.warn("[Tajeran Chat] Failed to initialize widget.", error);
      renderError("Chat is temporarily unavailable.");
    } finally {
      state.loading = false;
    }
  }

  function renderShell() {
    const settings = state.settings || {};
    const brandColor = settings.brand_color || "#16a34a";
    const position = settings.position === "bottom-left" ? "tj-left" : "tj-right";
    const title = settings.title || "Chat with us";
    const assistantName = settings.assistant_name || "Tajeran AI";
    const welcome = settings.welcome_message || "Hi! How can we help you today?";

    root.innerHTML = `
      <div class="tj-widget ${position}">
        <div class="tj-panel ${state.open ? "tj-open" : ""}">
          <div class="tj-header" style="background:${escapeAttr(brandColor)}">
            <div class="tj-avatar">AI</div>
            <div>
              <div class="tj-title">${escapeHtml(title)}</div>
              <div class="tj-subtitle">${escapeHtml(assistantName)}</div>
            </div>
            <button class="tj-close" type="button" aria-label="Close chat">×</button>
          </div>
          <div class="tj-messages">
            ${
              state.messages.length + state.notes.length
                ? renderConversation()
                : `<div class="tj-bubble tj-bubble-assistant">${escapeHtml(welcome)}</div>
                   <div class="tj-empty">Send a message and your Tajeran support workflow will handle it.</div>`
            }
          </div>
          ${
            state.selfService
              ? renderSelfServiceForm(brandColor)
              : `${renderRating()}
          ${renderSelfServiceButtons()}
          <form class="tj-input-row">
            <input class="tj-input" name="message" placeholder="Write a message..." autocomplete="off" />
            <button class="tj-send" type="submit" style="background:${escapeAttr(brandColor)}" ${state.sending ? "disabled" : ""}>
              ${state.sending ? "..." : "Send"}
            </button>
          </form>`
          }
          <div class="tj-powered">Powered by <strong>Tajeran.ai</strong></div>
        </div>
        <button class="tj-launcher" type="button" aria-label="Open chat" style="background:${escapeAttr(brandColor)}">
          ${chatIcon()}
        </button>
      </div>
    `;

    root.querySelector(".tj-launcher")?.addEventListener("click", () => {
      state.open = !state.open;
      renderShell();
      scrollToBottom();
    });

    root.querySelector(".tj-close")?.addEventListener("click", () => {
      state.open = false;
      renderShell();
    });

    async function handleSend(event) {
      if (event) event.preventDefault();

      const input = root.querySelector(".tj-input-row .tj-input");
      const value = String(input?.value || "").trim();

      if (!value) return;

      if (input) input.value = "";

      await sendMessage(value);
    }

    root.querySelectorAll("[data-feedback]").forEach((button) => {
      button.addEventListener("click", () =>
        sendFeedback(button.getAttribute("data-message-id"), button.getAttribute("data-feedback") === "up"),
      );
    });

    root.querySelectorAll("[data-rating]").forEach((button) => {
      button.addEventListener("click", () => sendRating(Number(button.getAttribute("data-rating"))));
    });

    root.querySelectorAll("[data-self-service]").forEach((button) => {
      button.addEventListener("click", () => {
        state.selfService = { kind: button.getAttribute("data-self-service") };
        renderShell();
        root.querySelector(".tj-form .tj-input")?.focus();
      });
    });

    root.querySelector(".tj-cancel")?.addEventListener("click", () => {
      state.selfService = null;
      renderShell();
    });

    root.querySelector(".tj-form")?.addEventListener("submit", submitSelfService);

    root.querySelector(".tj-input-row")?.addEventListener("submit", handleSend);

    root.querySelector(".tj-input-row .tj-send")?.addEventListener("click", handleSend);

    root.querySelector(".tj-input-row .tj-input")?.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        handleSend(event);
      }
    });

    scrollToBottom();
  }

  function renderError(message) {
    root.innerHTML = `
      <div class="tj-widget tj-right">
        <div class="tj-panel tj-open">
          <div class="tj-error">${escapeHtml(message)}</div>
        </div>
      </div>
    `;
  }

  function lastAnswerId() {
    for (let index = state.messages.length - 1; index >= 0; index -= 1) {
      const message = state.messages[index];
      if (message.role !== "customer" && message.id) return message.id;
    }
    return null;
  }

  function renderMessage(message) {
    const role = message.role === "customer" ? "customer" : "assistant";
    const bubble = `<div class="tj-bubble tj-bubble-${role}">${escapeHtml(message.content || "")}</div>`;
    if (role !== "assistant" || !message.id || message.id !== lastAnswerId()) return bubble;
    if (message.feedback) return `${bubble}<div class="tj-feedback">Thanks for your feedback.</div>`;
    const id = escapeAttr(message.id);
    return `${bubble}
      <div class="tj-feedback">
        Was this helpful?
        <button type="button" data-feedback="up" data-message-id="${id}" aria-label="Yes, this was helpful">👍</button>
        <button type="button" data-feedback="down" data-message-id="${id}" aria-label="No, this wasn't helpful">👎</button>
      </div>`;
  }

  // Saved messages and this window's order-status answers, in time order.
  function renderConversation() {
    return [...state.messages, ...state.notes]
      .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
      .map((item) => (item.note ? renderNote(item) : renderMessage(item)))
      .join("");
  }

  function renderNote(note) {
    const link = /^https?:\/\//i.test(note.url || "")
      ? `<br><a href="${escapeAttr(note.url)}" target="_blank" rel="noopener noreferrer">Track your parcel</a>`
      : "";
    return `<div class="tj-bubble tj-bubble-${note.role}">${escapeHtml(note.content)}${link}</div>`;
  }

  function renderSelfServiceButtons() {
    const enabled = (state.settings && state.settings.self_service) || {};
    const buttons = Object.keys(SELF_SERVICE)
      .filter((kind) => enabled[kind])
      .map((kind) => `<button type="button" data-self-service="${kind}">${SELF_SERVICE[kind].label}</button>`);
    return buttons.length ? `<div class="tj-actions">${buttons.join("")}</div>` : "";
  }

  function renderSelfServiceForm(brandColor) {
    const { kind, busy, error } = state.selfService;
    const action = SELF_SERVICE[kind];
    return `
      <form class="tj-form">
        <div class="tj-form-title">${action.label}</div>
        <input class="tj-input" name="order_number" placeholder="Order number, for example #1006" aria-label="Order number" maxlength="40" autocomplete="off" required />
        ${
          kind === "track_order"
            ? `<input class="tj-input" name="email" type="email" placeholder="Email used for the order" aria-label="Email used for the order" value="${escapeAttr(customerEmail || "")}" required />`
            : `<textarea class="tj-input" name="description" rows="3" placeholder="${action.prompt}" aria-label="${action.prompt}" maxlength="2000" required></textarea>`
        }
        ${error ? `<div class="tj-form-error" role="alert">${escapeHtml(error)}</div>` : ""}
        <div class="tj-form-buttons">
          <button class="tj-cancel" type="button">Cancel</button>
          <button class="tj-send" type="submit" style="background:${escapeAttr(brandColor)}" ${busy ? "disabled" : ""}>
            ${busy ? "..." : action.submit}
          </button>
        </div>
      </form>`;
  }

  async function submitSelfService(event) {
    event.preventDefault();
    const current = state.selfService;
    if (!current || current.busy) return;

    const values = Object.fromEntries(new FormData(event.target).entries());
    const orderNumber = String(values.order_number || "").trim();
    const form = event.target;
    current.busy = true;
    form.querySelector(".tj-send").disabled = true;

    try {
      await ensureSession();
      const base = `${apiBase}/sessions/${state.sessionId}`;

      if (current.kind === "track_order") {
        const order = await fetchJson(`${base}/track-order`, {
          method: "POST",
          body: { order_number: orderNumber, email: values.email },
        });
        const created_at = new Date().toISOString();
        state.notes.push({ note: true, created_at, role: "customer", content: `Track my order ${orderNumber}` });
        state.notes.push({ note: true, created_at, ...orderStatusNote(order) });
      } else {
        await fetchJson(`${base}/requests`, {
          method: "POST",
          body: { kind: current.kind, order_number: orderNumber, description: values.description },
        });
      }

      state.selfService = null;
      await loadMessages();
    } catch (error) {
      console.warn("[Tajeran Chat] Self-service request failed.", error);
      current.busy = false;
      current.error = "That didn't work. Please try again, or write us a message.";
      form.querySelector(".tj-send").disabled = false;
      if (!form.querySelector(".tj-form-error")) {
        form
          .querySelector(".tj-form-buttons")
          .insertAdjacentHTML("beforebegin", `<div class="tj-form-error" role="alert">${escapeHtml(current.error)}</div>`);
      }
    }
  }

  function orderStatusNote(order) {
    if (!order.found) {
      return {
        role: "assistant",
        content:
          "We couldn't find an order with that number and email. Please check both, or write us a message and our team will help.",
      };
    }
    if (!order.shipped) {
      return {
        role: "assistant",
        content: `Order ${order.order_name} ${order.paid ? "is paid and" : "is awaiting payment and"} hasn't shipped yet.`,
      };
    }
    const tracking = order.tracking_number
      ? ` Tracking number: ${order.tracking_number}${order.carrier ? ` (${order.carrier})` : ""}.`
      : " There is no tracking number for it yet.";
    return { role: "assistant", content: `Order ${order.order_name} has shipped.${tracking}`, url: order.tracking_url };
  }

  // Ask once per chat, after the customer has had an answer.
  function renderRating() {
    if (!state.sessionId || !lastAnswerId()) return "";
    if (state.ratedSessionId === state.sessionId) return "";
    return `
      <div class="tj-rating" role="group" aria-label="Rate this chat">
        <span>How was this chat?</span>
        ${[1, 2, 3, 4, 5]
          .map((score) => `<button type="button" data-rating="${score}" aria-label="${score} out of 5">${score}</button>`)
          .join("")}
      </div>`;
  }

  async function sendFeedback(messageId, helpful) {
    const message = state.messages.find((item) => item.id === messageId);
    if (!message || message.feedback) return;
    message.feedback = helpful ? "helpful" : "not_helpful";
    renderShell();
    try {
      await fetchJson(`${apiBase}/sessions/${state.sessionId}/messages/${messageId}/feedback`, {
        method: "POST",
        body: { helpful },
      });
    } catch (error) {
      console.warn("[Tajeran Chat] Failed to send feedback.", error);
    }
  }

  async function sendRating(score) {
    const sessionId = state.sessionId;
    state.ratedSessionId = sessionId;
    localStorage.setItem(ratedKey, sessionId);
    renderShell();
    try {
      await fetchJson(`${apiBase}/sessions/${sessionId}/rating`, { method: "POST", body: { score } });
    } catch (error) {
      console.warn("[Tajeran Chat] Failed to send rating.", error);
    }
  }

  async function ensureSession() {
    if (state.sessionId) return state.sessionId;

    const session = await fetchJson(`${apiBase}/sessions`, {
      method: "POST",
      body: {
        visitor_id: state.visitorId,
        channel: "website",
        customer_name: customerName,
        customer_email: customerEmail,
      },
    });

    state.sessionId = session.id;
    localStorage.setItem(sessionKey, state.sessionId);
    return state.sessionId;
  }

  async function loadMessages() {
    if (!state.sessionId) return;

    const messages = await fetchJson(`${apiBase}/sessions/${state.sessionId}/messages`);
    state.messages = Array.isArray(messages) ? messages : [];
    renderShell();
  }

  async function sendMessage(content) {
    try {
      state.sending = true;
      await ensureSession();

      const message = await fetchJson(`${apiBase}/sessions/${state.sessionId}/messages`, {
        method: "POST",
        body: { content },
      });

      state.messages = mergeMessages([...state.messages, message]);
      renderShell();
      await delayedLoad();
    } catch (error) {
      console.warn("[Tajeran Chat] Failed to send message.", error);
    } finally {
      state.sending = false;
      renderShell();
    }
  }

  async function delayedLoad() {
    await sleep(900);
    await loadMessages();
    await sleep(2200);
    await loadMessages();
    await sleep(4500);
    await loadMessages();
  }

  function startPolling() {
    stopPolling();
    state.pollTimer = window.setInterval(() => {
      const active = document.activeElement;
      const typing = active && active.classList && active.classList.contains("tj-input");

      if (state.open && state.sessionId && !typing && !state.sending && !state.selfService) {
        loadMessages().catch(() => {});
      }
    }, 3500);
  }

  function stopPolling() {
    if (state.pollTimer) {
      window.clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function mergeMessages(messages) {
    const seen = new Set();
    return messages.filter((message) => {
      const key = message.id || `${message.role}:${message.content}:${message.created_at || ""}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, {
      method: options.method || "GET",
      headers: {
        "Content-Type": "application/json",
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      mode: "cors",
      credentials: "omit",
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`HTTP ${response.status}: ${text}`);
    }

    return response.json();
  }

  function getOrCreateVisitorId() {
    const existing = localStorage.getItem(visitorKey);
    if (existing) return existing;

    const id =
      crypto?.randomUUID?.() ||
      `visitor_${Date.now()}_${Math.random().toString(16).slice(2)}`;

    localStorage.setItem(visitorKey, id);
    return id;
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      const messages = root.querySelector(".tj-messages");
      if (messages) messages.scrollTop = messages.scrollHeight;
    });
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function escapeAttr(value) {
    return escapeHtml(value).replaceAll("`", "&#096;");
  }

  function chatIcon() {
    return `
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M7.5 18.5 4 20l1.15-3.45A8 8 0 1 1 7.5 18.5Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
        <path d="M8 11.5h8M8 8.5h5M8 14.5h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    `;
  }
})();
