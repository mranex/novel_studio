from __future__ import annotations

import uuid
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from app.schemas import IDCounter
from app.storage import read_json, resolve_project_path, write_json_atomic


COUNTER_KEYS = {
    "glossary": ("glossary_next", "glo"),
    "relationship": ("relationship_next", "rel"),
    "job": ("job_next", "job"),
}


@contextmanager
def _counter_lock(project_root: str | Path):
    lock_path = resolve_project_path(project_root, "db", "counters.lock")
    deadline = time.monotonic() + 5
    fd: int | None = None
    try:
        while True:
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode("utf-8"))
                break
            except FileExistsError:
                if time.monotonic() > deadline:
                    raise TimeoutError("Could not acquire counters lock")
                time.sleep(0.05)
        yield
    finally:
        if fd is not None:
            os.close(fd)
            lock_path.unlink(missing_ok=True)


def allocate_id(project_root: str | Path, kind: Literal["glossary", "relationship", "job"]) -> str:
    key, prefix = COUNTER_KEYS[kind]
    counters_path = resolve_project_path(project_root, "db", "counters.json")
    try:
        with _counter_lock(project_root):
            counters = read_json(counters_path, IDCounter)
            value = counters.next_value(key)  # type: ignore[arg-type]
            write_json_atomic(counters_path, counters, IDCounter)
            return f"{prefix}_{value:06d}"
    except (OSError, TimeoutError):
        return f"{prefix}_{uuid.uuid4().hex}"
