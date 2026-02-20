import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");
const list = document.getElementById("list");

async function requireAuth() {
  const { data } = await supabase.auth.getUser();
  if (!data?.user) window.location.href = "auth.html";
  return data.user;
}

function badge(status) {
  const map = { sent: "secondary", viewed: "info", shortlisted: "warning", hired: "success" };
  return `<span class="badge bg-${map[status] || "secondary"}">${status}</span>`;
}

async function getOrCreateConversation(jobId, workerId, employerId) {
  // try existing
  const { data: existing } = await supabase
    .from("conversations")
    .select("id")
    .eq("job_id", jobId)
    .eq("worker_id", workerId)
    .eq("employer_id", employerId)
    .maybeSingle();

  if (existing?.id) return existing.id;

  // create
  const { data: created, error } = await supabase
    .from("conversations")
    .insert({ job_id: jobId, worker_id: workerId, employer_id: employerId })
    .select("id")
    .single();

  if (error) throw error;
  return created.id;
}

async function main() {
  const user = await requireAuth();
  msg.textContent = "Loading...";

  const { data: apps, error } = await supabase
    .from("applications")
    .select("id, status, created_at, job_id, worker_id, jobs:job_id ( id, title, city, employer_id )")
    .eq("worker_id", user.id)
    .order("created_at", { ascending: false });

  msg.textContent = "";
  if (error) {
    list.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
    return;
  }

  if (!apps?.length) {
    list.innerHTML = `<div class="alert alert-light">No applications yet.</div>`;
    return;
  }

  list.innerHTML = "";
  for (const a of apps) {
    const j = a.jobs;
    const canChat = a.status === "shortlisted" || a.status === "hired";

    const card = document.createElement("div");
    card.className = "card mb-3";
    card.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <h5 class="mb-1">${j?.title ?? "Job"}</h5>
            <div class="text-muted">${j?.city ?? "—"}</div>
          </div>
          <div>${badge(a.status)}</div>
        </div>

        <div class="mt-3">
          ${canChat ? `<button class="btn btn-primary btn-sm" data-chat="1">Open Chat</button>` : ""}
        </div>
      </div>
    `;

    if (canChat) {
      card.querySelector('button[data-chat="1"]').addEventListener("click", async () => {
        try {
          const convId = await getOrCreateConversation(j.id, user.id, j.employer_id);
          window.location.href = `chat.html?c=${convId}`;
        } catch (e) {
          alert(e.message);
        }
      });
    }

    list.appendChild(card);
  }

  document.getElementById("logoutBtn").addEventListener("click", async () => {
    await supabase.auth.signOut();
    window.location.href = "auth.html";
  });
}

main();
