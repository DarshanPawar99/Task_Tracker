# Task Tracker - Streamlit + Supabase

A simple internal task tracker built with Streamlit and Supabase.

## Files in this repo

- `app.py` -> Streamlit UI
- `supabase_storage.py` -> Supabase read/write layer
- `requirements.txt` -> Python dependencies
- `.gitignore` -> prevents secrets/local files from being pushed

---

## 1) Create Supabase table

Open **Supabase -> SQL Editor** and run this:

```sql
create table if not exists public.tasks (
  id text primary key,
  name text not null,
  status text not null default 'Not Started',
  intensity text not null default 'Medium',
  received_date date,
  due_date date,
  submitted_date date,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Then run this:

```sql
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace trigger trg_tasks_updated_at
before update on public.tasks
for each row
execute function public.set_updated_at();
```

If needed, also run:

```sql
alter table public.tasks enable row level security;
```

---

## 2) Get Supabase credentials

From your Supabase project, copy:

- `Project URL`
- `API Key`

You will use them in Streamlit secrets.

---

## 3) Create local secrets file

Create a folder named `.streamlit`

Inside it, create `secrets.toml`

```toml
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_KEY = "your-api-key"
```

Do **not** push this file to GitHub.

---

## 4) Install packages locally

```bash
pip install -r requirements.txt
```

---

## 5) Run locally

```bash
streamlit run app.py
```

---

## 6) Deploy on Streamlit Community Cloud

1. Push these files to GitHub:
   - `app.py`
   - `supabase_storage.py`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`

2. In Streamlit Community Cloud:
   - create a new app
   - connect your GitHub repo
   - select `app.py`

3. In app settings/secrets, add:

```toml
SUPABASE_URL = "https://your-project-ref.supabase.co"
SUPABASE_KEY = "your-api-key"
```

4. Deploy the app

---

## 7) Features

- Add task
- Edit task
- Delete task
- Search task
- Filter by status
- Sort by due date / received / status / intensity / urgency
- Auto urgency calculation
- CSV download

---

## 8) Task fields used

- `id`
- `name`
- `status`
- `intensity`
- `receivedDate`
- `dueDate`
- `submittedDate`
- `notes`

Database columns:

- `id`
- `name`
- `status`
- `intensity`
- `received_date`
- `due_date`
- `submitted_date`
- `notes`
- `created_at`
- `updated_at`

---

## 9) Notes

- This is designed for internal use.
- Data is stored in Supabase, not in local JSON or Excel.
- If the app cannot connect, check:
  - secrets are correct
  - Supabase table exists
  - API key is correct

---

## 10) Repo structure

```text
task-tracker/
│
├── app.py
├── supabase_storage.py
├── requirements.txt
├── README.md
├── .gitignore
└── .streamlit/
    └── secrets.toml
```
