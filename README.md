# ITENT-15x

## Local Django: fake data and admin UI

1. **Install and migrate** (from project root): `pip install -r requirements.txt` then `python manage.py migrate`.

2. **Load demo users and jobs**:
   ```bash
   python manage.py populate_testdata
   ```
   Test accounts use usernames like `test_worker_01` / `test_employer_01` and password `TestPass123!`.

3. **Remove all fake data**:
   ```bash
   python manage.py populate_testdata --clear
   ```

4. **In-app staff console** (metrics, verification, jobs, applications, users, conversations):
   - **Home:** `/accounts/staff/`
   - **Employer / worker verification:** `/accounts/staff/verification/employers/` and `/accounts/staff/verification/workers/`
   - Legacy URLs `/accounts/admin-dashboard/` and `/accounts/admin-workers/` redirect to those verification pages.
   - **Django superusers** can open the staff console even if their `role` is still `worker` (e.g. after `createsuperuser`).
   - On verification pages the default filter is **Pending**. Use **Lahat** or **Verified** to see most seeded employers/workers.

5. **Django site admin** (`/admin/`): full model access and editing—use alongside the staff console when you need raw rows or fields not exposed in the custom UI.

### User uploads (avatars, verification documents)

With `DEBUG=False`, `/media/` is served from `MEDIA_ROOT` via URL routing in `itent/urls.py`. On hosts such as **Render (free web service)**, the filesystem is **ephemeral**: redeploys can delete uploaded files even though database rows still reference them. For a public launch where files must survive deploys, use **durable object storage** (for example Cloudinary’s free tier or S3-compatible storage with `django-storages`) and point `DEFAULT_FILE_STORAGE` at that backend.

## Supabase `profiles` setup

For sign-up/login to save roles, you need a `profiles` table and RLS policies.

**Table** (Supabase SQL Editor):

```sql
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'worker'
);

alter table public.profiles enable row level security;

create policy "Users can insert own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

create policy "Users can read own profile"
  on public.profiles for select
  using (auth.uid() = id);
```

Run the app via Live Server from the **project root** (so both `public/` and `js/` are served), or open `public/` as the root and use `public/auth.html`.
