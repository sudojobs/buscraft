from __future__ import annotations
import json
from pathlib import Path
from typing import Union
from .models import Project


def load_project(path: Union[str, Path]) -> Project:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Project.from_dict(data)


def save_project(project: Project, path: Union[str, Path]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(project.to_dict(), f, indent=2)
