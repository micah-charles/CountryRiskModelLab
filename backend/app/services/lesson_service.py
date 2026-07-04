from __future__ import annotations

from pathlib import Path
import json

from app.models.schemas import Lesson


LESSON_DIR = Path(__file__).resolve().parents[1] / "lessons"


def list_lessons() -> list[Lesson]:
    lessons: list[Lesson] = []
    for path in sorted(LESSON_DIR.glob("*.json")):
        lessons.append(Lesson(**json.loads(path.read_text(encoding="utf-8"))))
    return lessons


def get_lesson(lesson_id: str) -> Lesson:
    for lesson in list_lessons():
        if lesson.lesson_id == lesson_id:
            return lesson
    raise ValueError(f"Lesson not found: {lesson_id}")

