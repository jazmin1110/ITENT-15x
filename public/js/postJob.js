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
  msg.textContent = "Posting...";

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
    msg.textContent = "Please fill in job title and city.";
    return;
  }

  const { error } = await supabase
    .from("jobs")
    .insert(payload);

  if (error) {
    msg.textContent = "Post failed: " + error.message;
    return;
  }

  msg.textContent = "Job posted ✅";
  setTimeout(() => window.location.href = "employer-profile.html", 900);
}

const user = await requireEmployer();

document.getElementById("postBtn").addEventListener("click", async () => {
  await postJob(user);
});
