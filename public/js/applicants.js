import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");
const appList = document.getElementById("appList");

function getJobId() {
  return new URLSearchParams(window.location.search).get("job");
}

async function requireEmployer() {
  const { data } = await supabase.auth.getUser();
  if (!data?.user) window.location.href = "auth.html";

  const { data: prof, error } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", data.user.id)
    .single();

  if (error || prof?.role !== "employer") {
    alert("Employer access only.");
    window.location.href = "worker-profile.html";
  }

  return data.user;
}

function renderLoading() {
  appList.innerHTML = `
    <div class="card mb-3"><div class="card-body placeholder-glow"><span class="placeholder col-5"></span><span class="placeholder col-3 ms-2"></span><div class="placeholder col-12 mt-2"></div></div></div>
    <div class="card mb-3"><div class="card-body placeholder-glow"><span class="placeholder col-6"></span><span class="placeholder col-4 ms-2"></span><div class="placeholder col-12 mt-2"></div></div></div>
  `;
}

function renderEmpty() {
  appList.innerHTML = `
    <div class="alert alert-light text-center py-5">
      <p class="mb-0">Wala pang applicants. Share your job post to get more applicants.</p>
    </div>
  `;
}

function statusBadge(status) {
  const map = {
    sent: "secondary",
    viewed: "info",
    shortlisted: "warning",
    hired: "success"
  };
  const cls = map[status] || "secondary";
  return `<span class="badge bg-${cls}">${status}</span>`;
}

async function updateStatus(appId, newStatus) {
  const { error } = await supabase
    .from("applications")
    .update({ status: newStatus })
    .eq("id", appId);

  if (error) throw error;
}

// ✅ Step 4: create conversation automatically when shortlisted/hired
async function getOrCreateConversation(jobId, workerId, employerId) {
  const { data: existing, error: e1 } = await supabase
    .from("conversations")
    .select("id")
    .eq("job_id", jobId)
    .eq("worker_id", workerId)
    .eq("employer_id", employerId)
    .maybeSingle();

  if (e1) throw e1;
  if (existing?.id) return existing.id;

  const { data: created, error: e2 } = await supabase
    .from("conversations")
    .insert({ job_id: jobId, worker_id: workerId, employer_id: employerId })
    .select("id")
    .single();

  if (e2) throw e2;
  return created.id;
}

async function main() {
  const employerUser = await requireEmployer();
  const jobId = getJobId();

  if (!jobId) {
    appList.innerHTML = `<div class="alert alert-danger">Missing job id.</div>`;
    return;
  }

  msg.textContent = "Loading applicants...";
  renderLoading();

  // Fetch applications first
  const { data: apps, error } = await supabase
    .from("applications")
    .select("id, status, created_at, worker_id")
    .eq("job_id", jobId)
    .order("created_at", { ascending: false });

  msg.textContent = "";
  if (error) {
    appList.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
    return;
  }

  if (!apps?.length) {
    renderEmpty();
    return;
  }

  // Fetch worker profiles separately
  const workerIds = [...new Set(apps.map((a) => a.worker_id).filter(Boolean))];
  const { data: workerProfiles } = await supabase
    .from("worker_profiles")
    .select("user_id, full_name, city, years_experience, skills, contact_number")
    .in("user_id", workerIds);

  const wpByid = Object.fromEntries((workerProfiles || []).map((wp) => [wp.user_id, wp]));

  appList.innerHTML = "";

  for (const app of apps) {
    const wp = wpByid[app.worker_id];
    const skills = (wp?.skills || []).join(", ") || "—";
    const exp = wp?.years_experience ?? "—";

    // ✅ Step 5: hide contact until hired
    const contact = (app.status === "hired")
      ? (wp?.contact_number ?? "—")
      : "Hidden until hired";

    const card = document.createElement("div");
    card.className = "card mb-3";

    card.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <h5 class="mb-1">${wp?.full_name ?? "Unknown Worker"}</h5>
            <div class="text-muted">${wp?.city ?? "—"} • ${exp} yrs exp</div>
          </div>
          <div>${statusBadge(app.status)}</div>
        </div>

        <div class="mt-2 small"><span class="text-muted">Skills:</span> ${skills}</div>
        <div class="mt-2 small"><span class="text-muted">Contact:</span> ${contact}</div>

        <div class="mt-3 d-flex gap-2 flex-wrap">
          <button class="btn btn-outline-info btn-sm" data-action="viewed">Mark Viewed</button>
          <button class="btn btn-outline-warning btn-sm" data-action="shortlisted">Shortlist</button>
          <button class="btn btn-outline-success btn-sm" data-action="hired">Mark Hired</button>
          <button class="btn btn-outline-primary btn-sm" data-chat="1" ${app.status === "shortlisted" || app.status === "hired" ? "" : "disabled"}>
            Open Chat
          </button>
        </div>
      </div>
    `;

    // Status buttons
    card.querySelectorAll("button[data-action]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const newStatus = btn.dataset.action;
        btn.disabled = true;
        msg.textContent = "Updating status...";

        try {
          await updateStatus(app.id, newStatus);

          // ✅ Step 4: auto-create conversation when shortlisted/hired
          if (newStatus === "shortlisted" || newStatus === "hired") {
            await getOrCreateConversation(jobId, app.worker_id, employerUser.id);
          }

          msg.textContent = "Updated ✅";
          setTimeout(() => window.location.reload(), 400);
        } catch (e) {
          msg.textContent = "";
          alert(e.message);
          btn.disabled = false;
        }
      });
    });

    // Open chat button
    card.querySelector('button[data-chat="1"]').addEventListener("click", async () => {
      if (!(app.status === "shortlisted" || app.status === "hired")) return;

      try {
        msg.textContent = "Opening chat...";
        const convId = await getOrCreateConversation(jobId, app.worker_id, employerUser.id);
        window.location.href = `chat.html?c=${convId}`;
      } catch (e) {
        msg.textContent = "";
        alert(e.message);
      }
    });

    appList.appendChild(card);
  }
}

main();