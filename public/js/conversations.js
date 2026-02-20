import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");
const conversationsList = document.getElementById("conversationsList");

async function requireAuth() {
  const { data } = await supabase.auth.getUser();
  if (!data?.user) window.location.href = "auth.html";
  return data.user;
}

function setupNavbar(role) {
  const navBrand = document.getElementById("navBrand");
  const navLinks = document.getElementById("navLinks");
  const navbar = document.getElementById("conversationsNavbar");

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

async function loadConversations(user, role) {
  msg.textContent = "Loading conversations...";

  let conversations;
  if (role === "worker") {
    const { data, error } = await supabase
      .from("conversations")
      .select("id, created_at, job_id, employer_id")
      .eq("worker_id", user.id)
      .order("created_at", { ascending: false });

    if (error) throw error;
    conversations = data || [];
  } else {
    const { data, error } = await supabase
      .from("conversations")
      .select("id, created_at, job_id, worker_id")
      .eq("employer_id", user.id)
      .order("created_at", { ascending: false });

    if (error) throw error;
    conversations = data || [];
  }

  // Fetch jobs and profiles separately
  const jobIds = [...new Set(conversations.map(c => c.job_id).filter(Boolean))];
  const { data: jobs } = await supabase
    .from("jobs")
    .select("id, title, city")
    .in("id", jobIds);

  const jobsById = Object.fromEntries((jobs || []).map(j => [j.id, j]));

  if (role === "worker") {
    const employerIds = [...new Set(conversations.map(c => c.employer_id).filter(Boolean))];
    const { data: employerProfs } = await supabase
      .from("employer_profiles")
      .select("user_id, company_name")
      .in("user_id", employerIds);

    const profsById = Object.fromEntries((employerProfs || []).map(p => [p.user_id, p]));

    conversations = conversations.map(c => ({
      ...c,
      jobs: jobsById[c.job_id] || null,
      employer_profiles: profsById[c.employer_id] || null
    }));
  } else {
    const workerIds = [...new Set(conversations.map(c => c.worker_id).filter(Boolean))];
    const { data: workerProfs } = await supabase
      .from("worker_profiles")
      .select("user_id, full_name")
      .in("user_id", workerIds);

    const profsById = Object.fromEntries((workerProfs || []).map(p => [p.user_id, p]));

    conversations = conversations.map(c => ({
      ...c,
      jobs: jobsById[c.job_id] || null,
      worker_profiles: profsById[c.worker_id] || null
    }));
  }

  msg.textContent = "";
  return conversations;
}

function renderConversations(conversations, role) {
  if (!conversations.length) {
    conversationsList.innerHTML = `
      <div class="alert alert-light text-center py-5">
        <p class="mb-0">Wala pang conversations. Mag-chat kapag may shortlisted o hired na application.</p>
      </div>
    `;
    return;
  }

  conversationsList.innerHTML = "";
  conversations.forEach(conv => {
    const job = conv.jobs;
    const otherParty = role === "worker" 
      ? conv.employer_profiles?.company_name || "Employer"
      : conv.worker_profiles?.full_name || "Worker";
    
    const card = document.createElement("div");
    card.className = "card mb-3";
    card.innerHTML = `
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
          <div>
            <h5 class="mb-1">${job?.title || "Job"}</h5>
            <div class="text-muted small">${otherParty} • ${job?.city || "—"}</div>
          </div>
          <a href="chat.html?c=${conv.id}" class="btn btn-primary btn-sm">Open Chat</a>
        </div>
      </div>
    `;
    conversationsList.appendChild(card);
  });
}

async function main() {
  const user = await requireAuth();
  
  const { data: prof } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .maybeSingle();
  
  const role = prof?.role || "worker";
  setupNavbar(role);

  try {
    const conversations = await loadConversations(user, role);
    renderConversations(conversations, role);
  } catch (e) {
    msg.textContent = "";
    conversationsList.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
  }
}

main();
