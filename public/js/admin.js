import { supabase } from "./supabaseClient.js";

const msg = document.getElementById("msg");
const list = document.getElementById("list");

async function requireAdmin() {
  const { data } = await supabase.auth.getUser();
  if (!data?.user) window.location.href = "auth.html";

  const { data: prof, error } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", data.user.id)
    .single();

  if (error || !prof || prof.role !== "admin") {
    alert("Admin access only.");
    window.location.href = "auth.html";
  }

  return data.user;
}

async function loadEmployers() {
  msg.textContent = "Loading employer profiles...";

  const { data, error } = await supabase
    .from("employer_profiles")
    .select("user_id, company_name, city, contact_person, verified, doc_url, updated_at")
    .order("updated_at", { ascending: false });

  msg.textContent = "";
  if (error) {
    list.innerHTML = `<div class="alert alert-danger">${error.message}</div>`;
    return [];
  }

  return data || [];
}

async function toggleVerified(userId, nextValue) {
  const { error } = await supabase
    .from("employer_profiles")
    .update({ verified: nextValue })
    .eq("user_id", userId);

  if (error) throw error;
}

function render(employers) {
  if (!employers.length) {
    list.innerHTML = `<div class="alert alert-light">No employer profiles yet.</div>`;
    return;
  }

  list.innerHTML = `
    <div class="table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr>
            <th>Company</th>
            <th>City</th>
            <th>Contact</th>
            <th>Verified</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          ${employers.map(e => `
            <tr>
              <td><strong>${e.company_name}</strong></td>
              <td>${e.city}</td>
              <td>${e.contact_person ?? "—"}</td>
              <td>
                ${e.verified ? `<span class="badge bg-success">Verified</span>` : `<span class="badge bg-secondary">Not verified</span>`}
              </td>
              <td>
                <button class="btn btn-outline-primary btn-sm" data-id="${e.user_id}" data-next="${!e.verified}">
                  ${e.verified ? "Unverify" : "Verify"}
                </button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;

  document.querySelectorAll("button[data-id]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const userId = btn.dataset.id;
      const nextValue = btn.dataset.next === "true";
      btn.disabled = true;
      msg.textContent = "Updating...";

      try {
        await toggleVerified(userId, nextValue);
        msg.textContent = "Updated ✅";
        setTimeout(() => window.location.reload(), 400);
      } catch (e) {
        msg.textContent = "";
        alert(e.message);
        btn.disabled = false;
      }
    });
  });
}

await requireAdmin();
const employers = await loadEmployers();
render(employers);

document.getElementById("logoutBtn").addEventListener("click", async () => {
  await supabase.auth.signOut();
  window.location.href = "auth.html";
});
