"""tests/test_quiz_repo.py — QuizRepository integration tests."""
import pytest
from models.quiz import Quiz
from models.question import Question


class TestQuizRepository:
    def test_create_and_get_all(self, quiz_repo):
        quiz = quiz_repo.create("Physics Quiz", "Physics")
        assert quiz.id > 0
        all_quizzes = quiz_repo.get_all()
        assert any(q.id == quiz.id for q in all_quizzes)

    def test_get_by_id(self, quiz_repo):
        quiz = quiz_repo.create("Chemistry")
        found = quiz_repo.get_by_id(quiz.id)
        assert found is not None
        assert found.title == "Chemistry"

    def test_add_question_and_get(self, quiz_repo):
        quiz = quiz_repo.create("Math")
        q = quiz_repo.add_question(
            quiz_id=quiz.id,
            question_text="What is 2+2?",
            q_type="short",
            correct_answer="4",
        )
        assert q.id > 0
        questions = quiz_repo.get_questions(quiz.id)
        assert len(questions) == 1
        assert questions[0].question_text == "What is 2+2?"

    def test_delete_question(self, quiz_repo):
        quiz = quiz_repo.create("History")
        q = quiz_repo.add_question(quiz.id, "Q?", "short", "A")
        quiz_repo.delete_question(q.id)
        assert len(quiz_repo.get_questions(quiz.id)) == 0

    def test_delete_quiz_removes_questions(self, quiz_repo):
        quiz = quiz_repo.create("Delete Me")
        quiz_repo.add_question(quiz.id, "Q?", "short", "A")
        quiz_repo.delete(quiz.id)
        assert quiz_repo.get_by_id(quiz.id) is None
        assert len(quiz_repo.get_questions(quiz.id)) == 0

    def test_record_attempt(self, quiz_repo):
        quiz = quiz_repo.create("Scored Quiz")
        quiz_repo.record_attempt(quiz.id, 8, 10, 120)
        chart_data = quiz_repo.get_attempts_for_chart()
        assert any(r["title"] == "Scored Quiz" for r in chart_data)

    def test_question_count_in_quiz(self, quiz_repo):
        quiz = quiz_repo.create("Multi Q")
        quiz_repo.add_question(quiz.id, "Q1?", "short", "A1")
        quiz_repo.add_question(quiz.id, "Q2?", "truefalse", "True")
        found = quiz_repo.get_by_id(quiz.id)
        assert found.question_count == 2
