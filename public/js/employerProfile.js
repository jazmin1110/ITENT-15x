import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");

async function requireEmployer() {
  const { data } = await supabase.auth.getUser();
  if (!data?.user) window.location.href = "auth.html";

  // check role
  const { data: prof, error } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", data.user.id)
    .single();

  if (error || !prof) window.location.href = "auth.html";
  if (prof.role !== "employer") {
    alert("Employer access only.");
    window.location.href = "worker-profile.html";
  }

  return data.user;
}

async function loadEmployerProfile(user) {
  const { data, error } = await supabase
    .from("employer_profiles")
    .select("*")
    .eq("user_id", user.id)
    .maybeSingle();

  if (error) {
    msg.textContent = "Error loading profile: " + error.message;
    return;
  }

  if (!data) return;

  company_name.value = data.company_name ?? "";
  city.value = data.city ?? "";
  contact_person.value = data.contact_person ?? "";
}

async function saveEmployerProfile(user) {
  msg.textContent = "Saving...";
  const payload = {
    user_id: user.id,
    company_name: company_name.value.trim(),
    city: city.value.trim(),
    contact_person: contact_person.value.trim()
  };

  if (!payload.company_name || !payload.city) {
    msg.textContent = "Please fill in company name and city.";
    return;
  }

  const { error } = await supabase
    .from("employer_profiles")
    .upsert(payload);

  msg.textContent = error ? ("Save failed: " + error.message) : "Employer profile saved ✅";
}

const user = await requireEmployer();
await loadEmployerProfile(user);

document.getElementById("saveBtn").addEventListener("click", async () => {
  await saveEmployerProfile(user);
});

document.getElementById("logoutBtn").addEventListener("click", async () => {
  await supabase.auth.signOut();
  window.location.href = "auth.html";
});
