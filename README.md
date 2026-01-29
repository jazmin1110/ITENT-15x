# ITENT-15x

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
