import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");
const jobList = document.getElementById("jobList");

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
  jobList.innerHTML = `<div class="alert alert-light">Wala ka pang job posts.</div>`;
}

function renderJobs(jobs) {
  jobList.innerHTML = "";
  jobs.forEach(job => {
    const skills = (job.required_skills || []).join(", ") || "—";
    const rate = job.daily_rate ? `₱${job.daily_rate}/day` : "Rate not specified";

    const card = document.createElement("div");
    card.className = "card mb-3";
    card.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between">
          <div>
            <h5 class="card-title mb-1">${job.title}</h5>
            <div class="text-muted">${job.city} • Status: ${job.status}</div>
          </div>
          <div class="text-end">
            <div class="fw-semibold">${rate}</div>
          </div>
        </div>

        <div class="mt-2 small"><span class="text-muted">Skills:</span> ${skills}</div>

        <div class="mt-3">
          <a class="btn btn-primary btn-sm" href="applicants.html?job=${job.id}">
            View Applicants
          </a>
        </div>
      </div>
    `;
    jobList.appendChild(card);
  });
}

async function main() {
  const user = await requireEmployer();
  msg.textContent = "Loading your jobs...";

  const { data: jobs, error } = await supabase
    .from("jobs")
    .select("*")
    .eq("employer_id", user.id)
    .order("created_at", { ascending: false });

  console.log("EMPLOYER JOBS:", jobs, "ERROR:", error);

  msg.textContent = "";
  if (error) {
    jobList.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
    return;
  }

  if (!jobs?.length) renderEmpty();
  else renderJobs(jobs);

  document.getElementById("logoutBtn").addEventListener("click", async () => {
    await supabase.auth.signOut();
    window.location.href = "auth.html";
  });
}

main();
