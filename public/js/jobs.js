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
  jobList.innerHTML = `<div class="alert alert-light text-center py-5">Walang available jobs ngayon. Balik mamaya.</div>`;
}

function renderJobs(jobs) {
  jobList.innerHTML = "";
  jobs.forEach(job => {
    const requiredSkills = (job.required_skills || []).join(", ");
    const startDate = job.start_date ? new Date(job.start_date).toLocaleDateString() : "—";
    const rate = job.daily_rate ? `₱${job.daily_rate}/day` : "Rate not specified";
    const verified = job.employer_profiles?.verified;
    const badge = verified ? `<span class="badge bg-success ms-2">Verified</span>` : "";

    const card = document.createElement("div");
    card.className = "card mb-3";
    card.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between">
          <div>
            <h5 class="card-title mb-1">${job.title}${badge}</h5>
            <div class="text-muted">${job.city}</div>
          </div>
          <div class="text-end">
            <div class="fw-semibold">${rate}</div>
            <div class="small text-muted">Start: ${startDate}</div>
          </div>
        </div>

        <div class="mt-2 small text-muted">${requiredSkills || "—"}</div>

        <div class="mt-3">
          <a class="btn btn-primary btn-lg w-100" href="job.html?id=${job.id}">Tingnan • Apply</a>
        </div>
      </div>
    `;
    jobList.appendChild(card);
  });
}

async function fetchJobs() {
  msg.textContent = "Naglo-load...";

  const { data: jobs, error } = await supabase
    .from("jobs")
    .select("id, title, city, daily_rate, start_date, required_skills, employer_id, status")
    .eq("status", "open")
    .order("created_at", { ascending: false });

  if (error) {
    msg.textContent = "";
    jobList.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
    return [];
  }

  const employerIds = [...new Set((jobs || []).map((j) => j.employer_id).filter(Boolean))];
  let wpByid = {};
  if (employerIds.length) {
    const { data: profs } = await supabase
      .from("employer_profiles")
      .select("user_id, verified, company_name")
      .in("user_id", employerIds);
    wpByid = Object.fromEntries((profs || []).map((p) => [p.user_id, p]));
  }

  const enriched = (jobs || []).map((j) => ({
    ...j,
    employer_profiles: wpByid[j.employer_id] || null
  }));

  msg.textContent = "";
  return enriched;
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
