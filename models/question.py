"""models/question.py — Question domain model."""
from __future__ import annotations
from dataclasses import dataclass


VALID_TYPES = frozenset({"mcq", "truefalse", "short"})


@dataclass
class Question:
    """A single question in a quiz."""
    id: int
    quiz_id: int
    question_text: str
    q_type: str               # 'mcq' | 'truefalse' | 'short'
    correct_answer: str
    option_a: str = ""
    option_b: str = ""
    option_c: str = ""
    option_d: str = ""
    explanation: str = ""
    created_at: str = ""
    remote_id: str = ""
    is_dirty: int = 0
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.question_text.strip():
            raise ValueError("Question text cannot be empty.")
        if self.q_type not in VALID_TYPES:
            raise ValueError(
                f"q_type must be one of {VALID_TYPES}, got {self.q_type!r}"
            )
        if not self.correct_answer.strip():
            raise ValueError("Correct answer cannot be empty.")

    def check_answer(self, user_answer: str) -> bool:
        """Case-insensitive answer check."""
        return user_answer.strip().lower() == self.correct_answer.strip().lower()

    @property
    def mcq_options(self) -> list[str]:
        """Return non-empty MCQ options."""
        return [o for o in [self.option_a, self.option_b, self.option_c, self.option_d] if o]
