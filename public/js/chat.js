import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");
const thread = document.getElementById("thread");
const text = document.getElementById("text");
const warn = document.getElementById("warn");

function getConvId() {
  return new URLSearchParams(window.location.search).get("c");
}

async function requireAuth() {
  const { data } = await supabase.auth.getUser();
  if (!data?.user) window.location.href = "auth.html";
  return data.user;
}

function renderMessages(me, messages) {
  thread.innerHTML = "";
  for (const m of messages) {
    const mine = m.sender_id === me.id;
    const div = document.createElement("div");
    div.className = `mb-2 d-flex ${mine ? "justify-content-end" : "justify-content-start"}`;
    div.innerHTML = `
      <div class="px-3 py-2 rounded ${mine ? "bg-primary text-white" : "bg-light"}" style="max-width: 70%;">
        <div class="small">${m.content}</div>
        <div class="small opacity-75 mt-1">${new Date(m.created_at).toLocaleString()}</div>
      </div>
    `;
    thread.appendChild(div);
  }
  thread.scrollTop = thread.scrollHeight;
}

// Optional: soft discouragement of sharing numbers
function phoneWarning(input) {
  const looksLikeNumber = /(\+?63|0)\d{9,10}/.test(input) || /\b\d{10,}\b/.test(input);
  warn.textContent = looksLikeNumber
    ? "Reminder: For safety, avoid sharing phone numbers. Use in-app chat for coordination."
    : "";
}

async function loadThread(convId) {
  const { data, error } = await supabase
    .from("messages")
    .select("id, sender_id, content, created_at")
    .eq("conversation_id", convId)
    .order("created_at", { ascending: true });

  if (error) throw error;
  return data || [];
}

async function sendMessage(convId, user, content) {
  const { error } = await supabase
    .from("messages")
    .insert({ conversation_id: convId, sender_id: user.id, content });

  if (error) throw error;
}

function setupNavbar(role) {
  const navBrand = document.getElementById("navBrand");
  const navLinks = document.getElementById("navLinks");
  const navbar = document.getElementById("chatNavbar");

  if (role === "worker") {
    navbar.className = "navbar navbar-expand-sm navbar-dark bg-primary mb-4";
    navBrand.href = "worker-profile.html";
    navLinks.innerHTML = `
      <li class="nav-item"><a class="nav-link" href="worker-profile.html">My Profile</a></li>
      <li class="nav-item"><a class="nav-link" href="jobs.html">Browse Jobs</a></li>
      <li class="nav-item"><a class="nav-link" href="worker-applications.html">My Applications</a></li>
      <li class="nav-item"><a class="nav-link active" href="conversations.html">Chat</a></li>
    `;
  } else if (role === "employer") {
    navbar.className = "navbar navbar-expand-sm navbar-dark bg-success mb-4";
    navBrand.href = "employer-profile.html";
    navLinks.innerHTML = `
      <li class="nav-item"><a class="nav-link" href="employer-profile.html">My Profile</a></li>
      <li class="nav-item"><a class="nav-link" href="employer-jobs.html">My Jobs</a></li>
      <li class="nav-item"><a class="nav-link" href="post-job.html">Post Job</a></li>
      <li class="nav-item"><a class="nav-link active" href="conversations.html">Chat</a></li>
    `;
  }

  document.getElementById("logoutBtn").addEventListener("click", async () => {
    await supabase.auth.signOut();
    window.location.href = "auth.html";
  });
}

async function main() {
  const user = await requireAuth();
  
  // Setup navbar based on role
  const { data: prof } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .maybeSingle();
  setupNavbar(prof?.role || "worker");

  const convId = getConvId();

  if (!convId) {
    msg.innerHTML = `<div class="alert alert-danger">Missing conversation id.</div>`;
    return;
  }

  msg.textContent = "Loading messages...";
  try {
    const messages = await loadThread(convId);
    msg.textContent = "";
    renderMessages(user, messages);
  } catch (e) {
    msg.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
    return;
  }

  text.addEventListener("input", () => phoneWarning(text.value));

  document.getElementById("sendBtn").addEventListener("click", async () => {
    const content = text.value.trim();
    if (!content) return;

    document.getElementById("sendBtn").disabled = true;
    try {
      await sendMessage(convId, user, content);
      text.value = "";
      warn.textContent = "";
      const messages = await loadThread(convId);
      renderMessages(user, messages);
    } catch (e) {
      alert(e.message);
    } finally {
      document.getElementById("sendBtn").disabled = false;
    }
  });
}

main();
