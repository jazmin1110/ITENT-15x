import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");
const applyBtn = document.getElementById("applyBtn");

const titleEl = document.getElementById("title");
const metaEl = document.getElementById("meta");
const rateEl = document.getElementById("rate");
const startEl = document.getElementById("startDate");
const skillsEl = document.getElementById("skills");

function getJobId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("id");
}

async function requireAuth() {
  const { data } = await supabase.auth.getUser();
  if (!data?.user) window.location.href = "auth.html";
  return data.user;
}

async function loadJob(jobId) {
  const { data: job, error } = await supabase
    .from("jobs")
    .select("*")
    .eq("id", jobId)
    .single();

  if (error) throw error;
  return job;
}

function renderJob(job) {
  titleEl.textContent = job.title;
  metaEl.textContent = `${job.city} • Status: ${job.status}`;
  rateEl.textContent = job.daily_rate ? `₱${job.daily_rate}/day` : "Not specified";
  startEl.textContent = job.start_date ? new Date(job.start_date).toLocaleDateString() : "—";
  skillsEl.textContent = (job.required_skills || []).join(", ") || "—";
}

async function checkIfAlreadyApplied(jobId, userId) {
  const { data, error } = await supabase
    .from("applications")
    .select("id")
    .eq("job_id", jobId)
    .eq("worker_id", userId)
    .maybeSingle();

  if (error) return false; // if error, we still allow apply attempt
  return !!data;
}

async function applyToJob(jobId, userId) {
  msg.textContent = "Sending application...";

  const { error } = await supabase
    .from("applications")
    .insert({
      job_id: jobId,
      worker_id: userId
    });

  if (error) throw error;
}

async function main() {
  const user = await requireAuth();
  const jobId = getJobId();

  document.getElementById("logoutBtn")?.addEventListener("click", async () => {
    await supabase.auth.signOut();
    window.location.href = "auth.html";
  });

  if (!jobId) {
    msg.innerHTML = `<div class="alert alert-danger">Missing job id.</div>`;
    applyBtn.disabled = true;
    return;
  }

  try {
    msg.textContent = "Loading job...";
    const job = await loadJob(jobId);
    renderJob(job);
    msg.textContent = "";

    const already = await checkIfAlreadyApplied(jobId, user.id);
    if (already) {
      applyBtn.disabled = true;
      applyBtn.textContent = "Already Applied";
      msg.innerHTML = `<div class="alert alert-info mt-2">You already applied to this job.</div>`;
      return;
    }

    applyBtn.addEventListener("click", async () => {
      applyBtn.disabled = true;
      try {
        await applyToJob(jobId, user.id);
        applyBtn.textContent = "Application Sent ✅";
        msg.innerHTML = `<div class="alert alert-success mt-2">Na-send na ang application mo.</div>`;
      } catch (e) {
        applyBtn.disabled = false;
        msg.innerHTML = `<div class="alert alert-danger mt-2">${e.message}</div>`;
      }
    });

  } catch (e) {
    msg.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
    applyBtn.disabled = true;
  }
}

main();
