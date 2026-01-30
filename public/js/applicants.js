import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");
const appList = document.getElementById("appList");

function getJobId() {
  return new URLSearchParams(window.location.search).get("job");
}

async function requireEmployer() {
  const { data } = await supabase.auth.getUser();
  if (!data?.user) window.location.href = "auth.html";

  const { data: prof } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", data.user.id)
    .single();

  if (prof?.role !== "employer") {
    alert("Employer access only.");
    window.location.href = "worker-profile.html";
  }

  return data.user;
}

function renderEmpty() {
  appList.innerHTML = `<div class="alert alert-light">Wala pang applicants.</div>`;
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

async function main() {
  await requireEmployer();

  document.getElementById("logoutBtn")?.addEventListener("click", async () => {
    await supabase.auth.signOut();
    window.location.href = "auth.html";
  });

  const jobId = getJobId();
  if (!jobId) {
    appList.innerHTML = `<div class="alert alert-danger">Missing job id.</div>`;
    return;
  }

  msg.textContent = "Loading applicants...";

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

  // Fetch worker profiles (full_name, city, etc.) from worker_profiles table
  const workerIds = [...new Set(apps.map((a) => a.worker_id).filter(Boolean))];
  const { data: workerProfiles } = await supabase
    .from("worker_profiles")
    .select("user_id, full_name, city, years_experience, skills, contact_number")
    .in("user_id", workerIds);

  const wpByid = Object.fromEntries((workerProfiles || []).map((wp) => [wp.user_id, wp]));

  appList.innerHTML = "";
  apps.forEach((app) => {
    const wp = wpByid[app.worker_id];
    const skills = (wp?.skills || []).join(", ") || "—";
    const exp = (wp?.years_experience ?? "—");
    const contact = wp?.contact_number ?? "—";

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
        </div>
      </div>
    `;

    // attach click handlers
    card.querySelectorAll("button[data-action]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const newStatus = btn.dataset.action;
        btn.disabled = true;
        msg.textContent = "Updating status...";

        try {
          await updateStatus(app.id, newStatus);
          msg.textContent = "Updated ✅";
          setTimeout(() => window.location.reload(), 400);
        } catch (e) {
          msg.textContent = "";
          alert(e.message);
          btn.disabled = false;
        }
      });
    });

    appList.appendChild(card);
  });
}

main();
