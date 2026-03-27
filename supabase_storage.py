from __future__ import annotations

from typing import Any

import streamlit as st
from supabase import Client, create_client


TABLE_NAME = "tasks"


class SupabaseStorageError(Exception):
    pass


@st.cache_resource(show_spinner=False)
def get_supabase_client() -> Client:
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        raise SupabaseStorageError(
            "Missing SUPABASE_URL or SUPABASE_KEY in Streamlit secrets."
        )

    return create_client(url, key)


def _normalize_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": (task.get("id") or "").strip(),
        "name": (task.get("name") or "").strip(),
        "status": (task.get("status") or "Not Started").strip(),
        "intensity": (task.get("intensity") or "Medium").strip(),
        "received_date": task.get("receivedDate") or None,
        "due_date": task.get("dueDate") or None,
        "submitted_date": task.get("submittedDate") or None,
        "notes": (task.get("notes") or "").strip(),
    }


def _to_app_task(row: dict[str, Any]) -> dict[str, str]:
    return {
        "id": row.get("id") or "",
        "name": row.get("name") or "",
        "status": row.get("status") or "Not Started",
        "intensity": row.get("intensity") or "Medium",
        "receivedDate": row.get("received_date") or "",
        "dueDate": row.get("due_date") or "",
        "submittedDate": row.get("submitted_date") or "",
        "notes": row.get("notes") or "",
    }


def read_tasks() -> list[dict[str, str]]:
    try:
        client = get_supabase_client()
        response = (
            client.table(TABLE_NAME)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return [_to_app_task(row) for row in (response.data or [])]
    except Exception as exc:
        raise SupabaseStorageError(f"Failed to read tasks: {exc}") from exc


def upsert_task(task: dict[str, Any]) -> None:
    normalized = _normalize_task(task)

    if not normalized["id"]:
        raise SupabaseStorageError("Task id is required.")
    if not normalized["name"]:
        raise SupabaseStorageError("Task name is required.")

    try:
        client = get_supabase_client()
        client.table(TABLE_NAME).upsert(normalized).execute()
    except Exception as exc:
        raise SupabaseStorageError(f"Failed to save task: {exc}") from exc


def delete_task(task_id: str) -> None:
    if not task_id:
        raise SupabaseStorageError("Task id is required.")

    try:
        client = get_supabase_client()
        client.table(TABLE_NAME).delete().eq("id", task_id).execute()
    except Exception as exc:
        raise SupabaseStorageError(f"Failed to delete task: {exc}") from exc


def test_connection() -> tuple[bool, str]:
    try:
        client = get_supabase_client()
        client.table(TABLE_NAME).select("id").limit(1).execute()
        return True, "Supabase connection successful."
    except Exception as exc:
        return False, str(exc)
