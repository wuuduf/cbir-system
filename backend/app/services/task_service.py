"""In-process background task registry for local experiment workflows."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import get_settings

TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TaskRecord:
    """Runtime state for one background task."""

    id: str
    name: str
    kind: str
    status: str = "queued"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    command: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    returncode: int | None = None
    progress: dict[str, Any] = field(default_factory=dict)


class TaskManager:
    """Small task manager suitable for a single local FastAPI process."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._processes: dict[str, subprocess.Popen[str]] = {}
        self._lock = threading.Lock()

    def list_tasks(self) -> list[TaskRecord]:
        with self._lock:
            return sorted(
                self._tasks.values(), key=lambda task: task.created_at, reverse=True
            )

    def get(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            return self._tasks.get(task_id)

    def clear(self, mode: str = "finished") -> None:
        """Clear terminal tasks, or cancel and clear every task."""

        if mode not in {"finished", "all"}:
            raise ValueError(f"Unsupported task clear mode: {mode}")

        if mode == "all":
            with self._lock:
                processes = list(self._processes.values())
                self._tasks.clear()
                self._processes.clear()
            for process in processes:
                if process.poll() is None:
                    process.terminate()
            return

        with self._lock:
            finished_ids = [
                task_id
                for task_id, task in self._tasks.items()
                if task.status in TERMINAL_STATUSES
            ]
            for task_id in finished_ids:
                self._tasks.pop(task_id, None)

    def start_command(
        self,
        *,
        name: str,
        kind: str,
        command: list[str],
        cwd: Path | None = None,
        parser: str | None = None,
        progress: dict[str, Any] | None = None,
    ) -> TaskRecord:
        task = TaskRecord(
            id=uuid4().hex,
            name=name,
            kind=kind,
            command=command,
            progress=progress or {},
        )
        with self._lock:
            self._tasks[task.id] = task
        thread = threading.Thread(
            target=self._run_command,
            args=(task.id, command, cwd or get_settings().backend_root, parser),
            daemon=True,
        )
        thread.start()
        return task

    def cancel(self, task_id: str) -> TaskRecord | None:
        """Cancel a running task by terminating its subprocess."""

        with self._lock:
            task = self._tasks.get(task_id)
            process = self._processes.get(task_id)
            if task is None:
                return None
            if task.status not in {"queued", "running"}:
                return task
            task.status = "cancelling"
            task.updated_at = _now()
            if process is None:
                task.status = "cancelled"
                task.error = "任务已取消"
                return task
        if process is not None and process.poll() is None:
            process.terminate()
        self._append_log(task_id, "Task cancellation requested.")
        return task

    def _run_command(
        self, task_id: str, command: list[str], cwd: Path, parser: str | None
    ) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status in {"cancelled", "cancelling"}:
                return
            task.status = "running"
            task.updated_at = _now()
        started = time.perf_counter()
        try:
            process = subprocess.Popen(
                command,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            with self._lock:
                self._processes[task_id] = process
            assert process.stdout is not None
            for line in process.stdout:
                clean = line.rstrip()
                self._append_log(task_id, clean)
                self._parse_progress(task_id, clean, parser)
            returncode = process.wait()
            elapsed_ms = (time.perf_counter() - started) * 1000
            with self._lock:
                task = self._tasks.get(task_id)
                self._processes.pop(task_id, None)
                if task is None:
                    return
                task_status = task.status
            if task_status == "cancelling":
                self._update(
                    task_id,
                    status="cancelled",
                    returncode=returncode,
                    error="任务已取消",
                    result={"elapsed_ms": elapsed_ms},
                )
                return
            if returncode == 0:
                self._update(
                    task_id,
                    status="succeeded",
                    returncode=returncode,
                    result={"elapsed_ms": elapsed_ms},
                )
            else:
                self._update(
                    task_id,
                    status="failed",
                    returncode=returncode,
                    error=f"任务退出码: {returncode}",
                    result={"elapsed_ms": elapsed_ms},
                )
        except Exception as exc:  # noqa: BLE001 - task boundary records all errors
            self._append_log(task_id, f"ERROR: {exc}")
            with self._lock:
                self._processes.pop(task_id, None)
            self._update(task_id, status="failed", error=str(exc))

    def _append_log(self, task_id: str, line: str) -> None:
        if not line:
            return
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task.logs.append(line)
            if len(task.logs) > 500:
                task.logs = task.logs[-500:]
            task.updated_at = _now()

    def _parse_progress(self, task_id: str, line: str, parser: str | None) -> None:
        if parser != "train_json":
            return
        if not line.startswith("{"):
            return
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            return
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            if "epoch" in payload:
                task.progress.update(payload)
            if "best_acc" in payload:
                task.result = payload
            task.updated_at = _now()

    def _update(self, task_id: str, **changes: Any) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            for key, value in changes.items():
                setattr(task, key, value)
            task.updated_at = _now()


def python_command(module: str, *args: str) -> list[str]:
    """Return a venv-safe Python module command."""

    return [sys.executable, "-m", module, *args]


task_manager = TaskManager()
