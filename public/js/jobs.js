import { supabase } from "./supabaseClient.js";

const jobList = document.getElementById("jobList");
const msg = document.getElementById("msg");
const cityFilter = document.getElementById("cityFilter");
const skillFilter = document.getElementById("skillFilter");

async function requireAuth() {
  const { data } = await supabase.auth.getUser();
  if (!data?.user) window.location.href = "auth.html";
  return data.user;
}

function renderEmpty() {
  jobList.innerHTML = `<div class="alert alert-light">Walang available jobs ngayon.</div>`;
}

function renderJobs(jobs) {
  jobList.innerHTML = "";
  jobs.forEach(job => {
    const requiredSkills = (job.required_skills || []).join(", ");
    const startDate = job.start_date ? new Date(job.start_date).toLocaleDateString() : "—";
    const rate = job.daily_rate ? `₱${job.daily_rate}/day` : "Rate not specified";

    const card = document.createElement("div");
    card.className = "card mb-3";
    card.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between">
          <div>
            <h5 class="card-title mb-1">${job.title}</h5>
            <div class="text-muted">${job.city}</div>
          </div>
          <div class="text-end">
            <div class="fw-semibold">${rate}</div>
            <div class="small text-muted">Start: ${startDate}</div>
          </div>
        </div>

        <div class="mt-2 small">
          <span class="text-muted">Skills:</span> ${requiredSkills || "—"}
        </div>

        <div class="mt-3">
          <a class="btn btn-primary btn-sm" href="job.html?id=${job.id}">View Job</a>
        </div>
      </div>
    `;
    jobList.appendChild(card);
  });
}

async function fetchJobs() {
  msg.textContent = "Loading jobs...";

  // Basic query: open jobs only (matches your RLS policy)
  const { data: jobs, error } = await supabase
    .from("jobs")
    .select("*")
    .eq("status", "open")
    .order("created_at", { ascending: false });

  if (error) {
    msg.textContent = "Error loading jobs: " + error.message;
    jobList.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
    return [];
  }

  msg.textContent = "";
  return jobs || [];
}

function applyFilters(jobs) {
  const city = cityFilter.value.trim().toLowerCase();
  const skill = skillFilter.value.trim().toLowerCase();

  return jobs.filter(job => {
    const matchesCity = !city || (job.city || "").toLowerCase().includes(city);

    const skills = (job.required_skills || []).map(s => s.toLowerCase());
    const matchesSkill = !skill || skills.some(s => s.includes(skill));

    return matchesCity && matchesSkill;
  });
}

async function main() {
  await requireAuth();

  let jobs = await fetchJobs();
  if (!jobs.length) renderEmpty();
  else renderJobs(jobs);

  cityFilter.addEventListener("input", () => {
    const filtered = applyFilters(jobs);
    filtered.length ? renderJobs(filtered) : renderEmpty();
  });

  skillFilter.addEventListener("input", () => {
    const filtered = applyFilters(jobs);
    filtered.length ? renderJobs(filtered) : renderEmpty();
  });

  document.getElementById("logoutBtn").addEventListener("click", async () => {
    await supabase.auth.signOut();
    window.location.href = "auth.html";
  });
}

main();
