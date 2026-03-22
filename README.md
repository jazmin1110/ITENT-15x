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

4. **In-app “Admin Dashboard”** (verification queues at `/accounts/admin-dashboard/`):
   - **Django superusers** can open it even if their `role` is still `worker` (e.g. after `createsuperuser`).
   - The default tab is **Pending** only. Use **Lahat** or **Verified** to see most seeded employers/workers.

5. **Django site admin** (`/admin/`): lists all users including `test_*` if you use the same database as step 2 (default: `db.sqlite3` unless `DATABASE_URL` is set).

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
