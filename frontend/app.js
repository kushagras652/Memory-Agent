const $ = (selector) => document.querySelector(selector);
const conversation = $("#conversation");
const form = $("#chat-form");
const input = $("#message");
const userId = $("#user-id");
const accessForm = $("#access-form");
const accessUserId = $("#access-user-id");
const history = [];

function activeUser() { return userId.value.trim() || "default_user"; }
function escapeHtml(value) { const node = document.createElement("div"); node.textContent = value; return node.innerHTML; }
function addMessage(role, text) {
  $("#welcome")?.remove();
  const item = document.createElement("article");
  item.className = `message ${role}`;
  item.innerHTML = `<span class="message-label">${role === "user" ? "YOU" : "MEMORY AGENT"}</span><div class="bubble">${escapeHtml(text)}</div>`;
  conversation.append(item); conversation.scrollTop = conversation.scrollHeight;
  return item;
}
function addEvent(text) { const event = document.createElement("div"); event.className = "memory-event"; event.textContent = text; conversation.append(event); }
function resize() { input.style.height = "auto"; input.style.height = `${Math.min(input.scrollHeight, 150)}px`; }
function renderMemories(data) {
  const { summary, memories } = data;
  $("#memory-count").textContent = summary.total;
  $("#important-count").textContent = summary.high_importance;
  $("#inferred-count").textContent = summary.inferred;
  $("#memory-state").textContent = memories.length ? `${memories.length} ACTIVE` : "EMPTY";
  const list = $("#memory-list"); list.innerHTML = "";
  if (!memories.length) { list.innerHTML = '<p class="empty-memory">Share a durable preference, fact, or event and it will appear here.</p>'; return; }
  const template = $("#memory-template");
  memories.forEach((memory) => {
    const card = template.content.cloneNode(true);
    card.querySelector(".memory-type").textContent = memory.type;
    card.querySelector(".memory-source").textContent = memory.source === "inferred" ? "pattern" : "stated";
    card.querySelector("p").textContent = memory.content;
    card.querySelector(".importance span").style.setProperty("--strength", `${Math.max(8, memory.importance * 10)}%`);
    card.querySelector("small").textContent = `${memory.importance}/10`;
    list.append(card);
  });
}
async function loadMemories() {
  try { const res = await fetch(`/api/memories/${encodeURIComponent(activeUser())}`); if (!res.ok) throw new Error(); renderMemories(await res.json()); }
  catch { $("#memory-state").textContent = "OFFLINE"; }
}
async function send(message) {
  addMessage("user", message); history.push({ role: "user", content: message });
  const pending = addMessage("agent", "Thinking…"); pending.querySelector(".bubble").classList.add("thinking");
  $("#send").disabled = true;
  try {
    const res = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message, user_id: activeUser(), history: history.slice(0, -1) }) });
    const data = await res.json(); if (!res.ok) throw new Error(data.detail || "Unable to reach the agent.");
    pending.querySelector(".bubble").textContent = data.reply; history.push({ role: "assistant", content: data.reply });
    if (data.saved?.length) addEvent(`${data.saved.length} ${data.saved.length === 1 ? "memory" : "memories"} saved to your profile`);
    renderMemories({ summary: data.summary, memories: (await (await fetch(`/api/memories/${encodeURIComponent(activeUser())}`)).json()).memories });
  } catch (error) { pending.querySelector(".bubble").textContent = `I couldn't respond just now. ${error.message}`; }
  finally { $("#send").disabled = false; conversation.scrollTop = conversation.scrollHeight; }
}
form.addEventListener("submit", (event) => { event.preventDefault(); const message = input.value.trim(); if (!message) return; input.value = ""; resize(); send(message); });
input.addEventListener("input", resize);
input.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); form.requestSubmit(); } });
document.querySelectorAll("[data-prompt]").forEach((button) => button.addEventListener("click", () => { input.value = button.dataset.prompt; form.requestSubmit(); }));
$("#refresh").addEventListener("click", loadMemories);
$("#new-chat").addEventListener("click", () => { history.length = 0; conversation.innerHTML = '<div class="welcome" id="welcome"><div class="welcome-orb">✦</div><p class="eyebrow">FRESH CONVERSATION</p><h2>Start wherever you are.</h2><p>Your long-term memory remains available whenever it’s useful.</p></div>'; input.focus(); });
accessForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const id = accessUserId.value.trim();
  if (!id) return;
  userId.value = id;
  $("#profile-avatar").textContent = id.charAt(0).toUpperCase();
  $("#access-screen").classList.add("hidden");
  $(".app-shell").classList.add("ready");
  loadMemories();
  input.focus();
});
