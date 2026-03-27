from __future__ import annotations

import html
import uuid
from datetime import date, datetime
from textwrap import dedent

import pandas as pd
import streamlit as st

from supabase_storage import (
    SupabaseStorageError,
    delete_task,
    read_tasks,
    test_connection,
    upsert_task,
)


st.set_page_config(page_title="Task Tracker", page_icon="📋", layout="wide")

STATUS_OPTIONS = ["Not Started", "In Progress", "On Hold", "Under Review", "Completed"]
INTENSITY_OPTIONS = ["Low", "Medium", "High", "Critical"]
FILTER_STATUS = ["All", *STATUS_OPTIONS]

STATUS_ORDER = {
    "Not Started": 0,
    "In Progress": 1,
    "On Hold": 2,
    "Under Review": 3,
    "Completed": 4,
}

INTENSITY_ORDER = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
}

URGENCY_ORDER = {
    "Overdue": 0,
    "Urgent": 1,
    "Soon": 2,
    "On Track": 3,
    "Done": 4,
    "—": 5,
}

SORT_OPTIONS = {
    "Due Date": "dueDate",
    "Received": "receivedDate",
    "Status": "status",
    "Intensity": "intensity",
    "Urgency": "urgency",
}

STATUS_COLORS = {
    "Not Started": ("#f0f0f0", "#666"),
    "In Progress": ("#e8f4fd", "#1a6fa0"),
    "On Hold": ("#fff3e0", "#b36b00"),
    "Under Review": ("#f3e8ff", "#7b2cbf"),
    "Completed": ("#e8f5e9", "#2e7d32"),
}

INTENSITY_COLORS = {
    "Low": ("#e8f5e9", "#2e7d32", "#66bb6a"),
    "Medium": ("#fff8e1", "#f57f17", "#ffca28"),
    "High": ("#fff3e0", "#e65100", "#ff9800"),
    "Critical": ("#ffebee", "#c62828", "#ef5350"),
}

URGENCY_STYLE = {
    "Done": ("#e8f5e9", "#2e7d32"),
    "Overdue": ("#ffebee", "#c62828"),
    "Urgent": ("#fff3e0", "#e65100"),
    "Soon": ("#fff8e1", "#f57f17"),
    "On Track": ("#e3f2fd", "#1565c0"),
    "—": ("#f5f5f5", "#999"),
}

DEFAULT_TASK = {
    "id": "",
    "name": "",
    "status": "Not Started",
    "intensity": "Medium",
    "receivedDate": date.today().isoformat(),
    "dueDate": "",
    "submittedDate": "",
    "notes": "",
}


@st.cache_data(show_spinner=False, ttl=30)
def load_tasks_cached() -> list[dict[str, str]]:
    return read_tasks()


def clear_task_cache() -> None:
    load_tasks_cached.clear()


def render_html(content: str) -> None:
    st.markdown(dedent(content).strip(), unsafe_allow_html=True)


def inject_css() -> None:
    render_html("""
    <style>
    .stApp {
        background: #f6f7fb;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    .hero-card {
        background: white;
        border-radius: 18px;
        padding: 20px 22px;
        box-shadow: 0 8px 24px rgba(20, 20, 43, 0.06);
        margin-bottom: 18px;
    }
    .stat-card {
        background: white;
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 2px 8px rgba(20, 20, 43, 0.05);
        border-left: 4px solid #667eea;
    }
    .task-card {
        background: white;
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 4px 16px rgba(20, 20, 43, 0.05);
        margin-bottom: 12px;
        border: 1px solid #f0f0f5;
    }
    .task-name {
        font-size: 1rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 4px;
    }
    .task-notes {
        color: #8a8fa3;
        font-size: 0.83rem;
        line-height: 1.45;
        margin-bottom: 10px;
        white-space: pre-wrap;
    }
    .meta-row {
        color: #7b8194;
        font-size: 0.82rem;
        line-height: 1.5;
    }
    .pill {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .empty-state {
        background: white;
        border: 1.5px dashed #d9dde7;
        border-radius: 18px;
        padding: 52px 18px;
        text-align: center;
        color: #9aa1b2;
        box-shadow: 0 4px 16px rgba(20, 20, 43, 0.03);
    }
    .small-muted {
        color: #8f96a8;
        font-size: 0.85rem;
    }
    </style>
    """)


def parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def format_date(value: str | None) -> str:
    d = parse_date(value)
    return d.strftime("%d %b %Y") if d else ""


def days_between(a: str | None, b: str | None):
    da = parse_date(a)
    db = parse_date(b)
    if not da or not db:
        return None
    return (db - da).days


def get_derived_fields(task: dict) -> dict:
    today = date.today().isoformat()
    days_left = days_between(today, task.get("dueDate"))
    total_days = days_between(task.get("receivedDate"), task.get("dueDate"))
    turnaround = (
        days_between(task.get("receivedDate"), task.get("submittedDate"))
        if task.get("submittedDate")
        else None
    )

    if task.get("status") == "Completed":
        urgency = "Done"
    elif not task.get("dueDate"):
        urgency = "—"
    elif days_left is not None and days_left < 0:
        urgency = "Overdue"
    elif days_left is not None and days_left <= 2:
        urgency = "Urgent"
    elif days_left is not None and days_left <= 5:
        urgency = "Soon"
    else:
        urgency = "On Track"

    return {
        "daysLeft": days_left,
        "totalDays": total_days,
        "turnaround": turnaround,
        "urgency": urgency,
    }


def init_state() -> None:
    if "editing_id" not in st.session_state:
        st.session_state.editing_id = None
    if "form_mode" not in st.session_state:
        st.session_state.form_mode = "add"
    if "search" not in st.session_state:
        st.session_state.search = ""
    if "filter_status" not in st.session_state:
        st.session_state.filter_status = "All"
    if "sort_label" not in st.session_state:
        st.session_state.sort_label = "Due Date"
    if "sort_dir" not in st.session_state:
        st.session_state.sort_dir = "Ascending"


def validate_task(task_data: dict) -> str | None:
    if not task_data["name"].strip():
        return "Task name is required."

    received = parse_date(task_data.get("receivedDate"))
    due = parse_date(task_data.get("dueDate"))
    submitted = parse_date(task_data.get("submittedDate"))

    if received and due and due < received:
        return "Due date cannot be before received date."

    if received and submitted and submitted < received:
        return "Submitted date cannot be before received date."

    return None


def fetch_tasks() -> list[dict[str, str]]:
    return load_tasks_cached()


def get_task_by_id(tasks: list[dict], task_id: str | None):
    if not task_id:
        return None
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def get_processed_tasks(tasks: list[dict]) -> list[dict]:
    search = st.session_state.search.strip().lower()
    filter_status = st.session_state.filter_status
    sort_by = SORT_OPTIONS[st.session_state.sort_label]
    sort_dir = st.session_state.sort_dir

    filtered = []
    for task in tasks:
        if filter_status != "All" and task["status"] != filter_status:
            continue
        if search and search not in task["name"].lower() and search not in task.get("notes", "").lower():
            continue
        task_copy = dict(task)
        task_copy["derived"] = get_derived_fields(task_copy)
        filtered.append(task_copy)

    def sort_key(task: dict):
        if sort_by in {"dueDate", "receivedDate"}:
            return task.get(sort_by) or "9999-12-31"
        if sort_by == "intensity":
            return INTENSITY_ORDER[task["intensity"]]
        if sort_by == "status":
            return STATUS_ORDER[task["status"]]
        if sort_by == "urgency":
            return URGENCY_ORDER[task["derived"]["urgency"]]
        return task.get("name", "")

    return sorted(filtered, key=sort_key, reverse=(sort_dir == "Descending"))


def get_stats(tasks: list[dict]) -> dict:
    return {
        "total": len(tasks),
        "active": sum(1 for t in tasks if t["status"] != "Completed"),
        "overdue": sum(1 for t in tasks if get_derived_fields(t)["urgency"] == "Overdue"),
        "completed": sum(1 for t in tasks if t["status"] == "Completed"),
    }


def pill(label: str, bg: str, color: str) -> str:
    safe_label = html.escape(label)
    return f'<span class="pill" style="background:{bg};color:{color};">{safe_label}</span>'


def render_header() -> None:
    today_text = date.today().strftime("%A, %d %B %Y")
    col1, col2 = st.columns([4, 1.4])
    with col1:
        render_html(f"""
        <div class="hero-card">
            <div style="font-size: 2rem; font-weight: 800; color: #1a1a2e; margin-bottom: 4px;">Task Tracker ✦</div>
            <div class="small-muted">{html.escape(today_text)}</div>
        </div>
        """)
    with col2:
        render_html("<div style='height: 18px;'></div>")
        if st.button("↻ Refresh", use_container_width=True):
            clear_task_cache()
            st.rerun()


def render_connection_banner() -> None:
    with st.container(border=True):
        st.subheader("Supabase Setup")
        ok, message = test_connection()
        if ok:
            st.success(message)
            st.caption("Connected to Supabase tasks table.")
        else:
            st.error(message)


def render_stats(tasks: list[dict]) -> None:
    stats = get_stats(tasks)
    colors = {
        "Total": "#667eea",
        "Active": "#2196F3",
        "Overdue": "#ef5350",
        "Completed": "#4CAF50",
    }
    cols = st.columns(4)
    items = [
        ("Total", stats["total"]),
        ("Active", stats["active"]),
        ("Overdue", stats["overdue"]),
        ("Completed", stats["completed"]),
    ]
    for col, (label, value) in zip(cols, items):
        with col:
            render_html(f"""
            <div class="stat-card" style="border-left-color:{colors[label]}">
                <div style="font-size:1.7rem;font-weight:800;color:{colors[label]};line-height:1;">{value}</div>
                <div style="font-size:0.82rem;color:#8f96a8;margin-top:6px;font-weight:600;">{html.escape(label)}</div>
            </div>
            """)


def render_filters() -> None:
    c1, c2, c3, c4 = st.columns([2.4, 1.25, 1.25, 1])
    with c1:
        st.text_input("Search tasks", key="search", placeholder="Search by task name or notes...")
    with c2:
        st.selectbox("Filter by status", FILTER_STATUS, key="filter_status")
    with c3:
        st.selectbox("Sort by", list(SORT_OPTIONS.keys()), key="sort_label")
    with c4:
        st.selectbox("Direction", ["Ascending", "Descending"], key="sort_dir")


def render_task_form(tasks: list[dict]) -> None:
    mode = st.session_state.form_mode
    task = get_task_by_id(tasks, st.session_state.editing_id) if mode == "edit" else None
    initial = dict(task) if task else dict(DEFAULT_TASK)

    with st.container(border=True):
        st.subheader("Add New Task" if mode == "add" else "Edit Task")
        with st.form("task_form", clear_on_submit=False):
            name = st.text_input("Task Name *", value=initial.get("name", ""), placeholder="What needs to be done?")

            col1, col2 = st.columns(2)
            with col1:
                status = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(initial.get("status", "Not Started")))
            with col2:
                intensity = st.selectbox("Intensity", INTENSITY_OPTIONS, index=INTENSITY_OPTIONS.index(initial.get("intensity", "Medium")))

            col3, col4, col5 = st.columns(3)
            with col3:
                received = st.date_input(
                    "Received",
                    value=parse_date(initial.get("receivedDate")) or date.today(),
                    format="YYYY-MM-DD",
                )
            with col4:
                due_raw = parse_date(initial.get("dueDate"))
                due_enabled = st.checkbox("Set due date", value=bool(due_raw), key="due_toggle")
                due = st.date_input(
                    "Due Date",
                    value=due_raw or date.today(),
                    disabled=not due_enabled,
                    format="YYYY-MM-DD",
                )
            with col5:
                submitted_raw = parse_date(initial.get("submittedDate"))
                submitted_enabled = st.checkbox("Set submitted date", value=bool(submitted_raw), key="submitted_toggle")
                submitted = st.date_input(
                    "Submitted",
                    value=submitted_raw or date.today(),
                    disabled=not submitted_enabled,
                    format="YYYY-MM-DD",
                )

            notes = st.text_area("Notes", value=initial.get("notes", ""), height=90, placeholder="Optional notes...")

            save_col, clear_col, delete_col = st.columns([1.1, 1, 1])
            save_pressed = save_col.form_submit_button("Save Task", type="primary", use_container_width=True)
            clear_pressed = clear_col.form_submit_button("Clear / New", use_container_width=True)
            delete_pressed = False
            if mode == "edit":
                delete_pressed = delete_col.form_submit_button("Delete", use_container_width=True)

        if save_pressed:
            task_data = {
                "id": initial.get("id") or uuid.uuid4().hex[:12],
                "name": name.strip(),
                "status": status,
                "intensity": intensity,
                "receivedDate": received.isoformat() if received else "",
                "dueDate": due.isoformat() if due_enabled and due else "",
                "submittedDate": submitted.isoformat() if submitted_enabled and submitted else "",
                "notes": notes.strip(),
            }

            error = validate_task(task_data)
            if error:
                st.error(error)
            else:
                try:
                    upsert_task(task_data)
                    clear_task_cache()
                    st.session_state.editing_id = task_data["id"]
                    st.session_state.form_mode = "edit"
                    st.success("Task saved successfully.")
                    st.rerun()
                except SupabaseStorageError as exc:
                    st.error(str(exc))

        if clear_pressed:
            st.session_state.editing_id = None
            st.session_state.form_mode = "add"
            st.rerun()

        if delete_pressed and mode == "edit" and initial.get("id"):
            try:
                delete_task(initial["id"])
                clear_task_cache()
                st.session_state.editing_id = None
                st.session_state.form_mode = "add"
                st.success("Task deleted successfully.")
                st.rerun()
            except SupabaseStorageError as exc:
                st.error(str(exc))


def render_tasks(tasks: list[dict]) -> None:
    processed = get_processed_tasks(tasks)

    if not processed:
        message = "No tasks yet — add your first one!" if not tasks else "No tasks match your current filters."
        render_html(f"""
        <div class="empty-state">
            <div style="font-size: 2.2rem; margin-bottom: 10px;">📋</div>
            <div style="font-size: 1rem; font-weight: 700;">{html.escape(message)}</div>
        </div>
        """)
        return

    for task in processed:
        derived = task["derived"]
        status_bg, status_text = STATUS_COLORS[task["status"]]
        intensity_bg, intensity_text, _ = INTENSITY_COLORS[task["intensity"]]
        urgency_bg, urgency_text = URGENCY_STYLE[derived["urgency"]]

        safe_name = html.escape(task["name"])
        safe_notes = html.escape(task.get("notes", ""))
        notes_html = f'<div class="task-notes">{safe_notes}</div>' if safe_notes else ""

        meta_parts = []
        if task.get("receivedDate"):
            meta_parts.append(f"📥 Received: <b>{html.escape(format_date(task['receivedDate']))}</b>")
        if task.get("dueDate"):
            due_color = "#c62828" if derived["urgency"] == "Overdue" else "#555"
            meta_parts.append(f"📅 Due: <b style='color:{due_color}'>{html.escape(format_date(task['dueDate']))}</b>")
        if task.get("submittedDate"):
            meta_parts.append(f"✅ Submitted: <b style='color:#2e7d32'>{html.escape(format_date(task['submittedDate']))}</b>")
        if derived["daysLeft"] is not None and task["status"] != "Completed":
            if derived["daysLeft"] < 0:
                meta_parts.append(f"⏳ <span style='color:#c62828'>{abs(derived['daysLeft'])}d overdue</span>")
            else:
                meta_parts.append(f"⏳ {derived['daysLeft']}d left")
        if derived["turnaround"] is not None:
            meta_parts.append(f"⚡ Turnaround: <b style='color:#667eea'>{derived['turnaround']}d</b>")

        left, right = st.columns([5, 2.2], vertical_alignment="top")
        with left:
            render_html(f"""
            <div class="task-card">
                <div class="task-name">{safe_name}</div>
                {notes_html}
                <div style="margin-bottom:8px;">
                    {pill(task['status'], status_bg, status_text)}
                    {pill(task['intensity'], intensity_bg, intensity_text)}
                    {pill(task['derived']['urgency'], urgency_bg, urgency_text)}
                </div>
                <div class="meta-row">{' &nbsp;&nbsp;•&nbsp;&nbsp; '.join(meta_parts)}</div>
            </div>
            """)

        with right:
            with st.container(border=True):
                st.caption("Quick actions")
                selected_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(task["status"]),
                    key=f"status_{task['id']}",
                    label_visibility="collapsed",
                )
                if selected_status != task["status"]:
                    updated_task = dict(task)
                    updated_task["status"] = selected_status
                    if selected_status == "Completed" and not updated_task.get("submittedDate"):
                        updated_task["submittedDate"] = date.today().isoformat()
                    try:
                        upsert_task(updated_task)
                        clear_task_cache()
                        st.rerun()
                    except SupabaseStorageError as exc:
                        st.error(str(exc))

                action1, action2 = st.columns(2)
                if action1.button("Edit", key=f"edit_{task['id']}", use_container_width=True):
                    st.session_state.editing_id = task["id"]
                    st.session_state.form_mode = "edit"
                    st.rerun()
                if action2.button("Delete", key=f"delete_{task['id']}", use_container_width=True):
                    try:
                        delete_task(task["id"])
                        clear_task_cache()
                        if st.session_state.editing_id == task["id"]:
                            st.session_state.editing_id = None
                            st.session_state.form_mode = "add"
                        st.rerun()
                    except SupabaseStorageError as exc:
                        st.error(str(exc))


def render_download_section(tasks: list[dict]) -> None:
    if not tasks:
        return
    df = pd.DataFrame(tasks)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download tasks as CSV",
        csv,
        file_name="tasks_export.csv",
        mime="text/csv",
        use_container_width=True,
    )


def main() -> None:
    init_state()
    inject_css()

    render_header()
    render_connection_banner()
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    try:
        tasks = fetch_tasks()
    except Exception as exc:
        st.error(f"Could not load tasks: {exc}")
        tasks = []

    render_stats(tasks)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    left, right = st.columns([1.45, 2.1], vertical_alignment="top")
    with left:
        render_task_form(tasks)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        render_download_section(tasks)
    with right:
        render_filters()
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        render_tasks(tasks)


if __name__ == "__main__":
    main()
