import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");

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

function selectedSkills() {
  return [...document.querySelectorAll(".skill:checked")].map(cb => cb.value);
}

async function postJob(user) {
  const postBtn = document.getElementById("postBtn");
  postBtn.disabled = true;
  msg.className = "mt-3 alert alert-info";
  msg.textContent = "Nagpo-post...";
  msg.hidden = false;

  const payload = {
    employer_id: user.id,
    title: title.value.trim(),
    city: city.value.trim(),
    daily_rate: daily_rate.value ? Number(daily_rate.value) : null,
    required_skills: selectedSkills(),
    start_date: start_date.value || null,
    status: "open"
  };

  if (!payload.title || !payload.city) {
    postBtn.disabled = false;
    msg.className = "mt-3 alert alert-warning";
    msg.textContent = "Paki-lagay ang title at lungsod.";
    msg.hidden = false;
    return;
  }

  const { error } = await supabase
    .from("jobs")
    .insert(payload);

  if (error) {
    postBtn.disabled = false;
    msg.className = "mt-3 alert alert-danger";
    msg.textContent = "Error: " + error.message;
    msg.hidden = false;
    return;
  }

  msg.className = "mt-3 alert alert-success";
  msg.textContent = "Na-post na ✅";
  msg.hidden = false;
  setTimeout(() => window.location.href = "employer-jobs.html", 900);
}

const user = await requireEmployer();

document.getElementById("postBtn").addEventListener("click", async () => {
  await postJob(user);
});

document.getElementById("logoutBtn")?.addEventListener("click", async () => {
  await supabase.auth.signOut();
  window.location.href = "auth.html";
});
