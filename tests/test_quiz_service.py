"""tests/test_quiz_service.py — QuizService tests."""
import os
import csv
import tempfile
import pytest


class TestQuizService:
    def test_create_and_delete(self, quiz_service):
        quiz = quiz_service.create("Biology Quiz", "Biology")
        assert quiz.id > 0
        quiz_service.delete(quiz.id)
        assert quiz_service._repo.get_by_id(quiz.id) is None

    def test_add_question(self, quiz_service):
        quiz = quiz_service.create("Math")
        q = quiz_service.add_question(
            quiz.id, "2+2?", "short", "4", explanation="Basic arithmetic"
        )
        assert q.id > 0
        questions = quiz_service.get_questions(quiz.id)
        assert len(questions) == 1
        assert questions[0].explanation == "Basic arithmetic"

    def test_record_attempt(self, quiz_service):
        quiz = quiz_service.create("Timed")
        quiz_service.record_attempt(quiz.id, 7, 10, 90)
        chart = quiz_service.get_attempts_for_chart()
        assert any(r["title"] == "Timed" for r in chart)

    def test_csv_import_success(self, quiz_service, tmp_path):
        quiz = quiz_service.create("CSV Quiz")
        csv_file = tmp_path / "questions.csv"
        csv_file.write_text(
            "question,q_type,correct_answer,option_a,option_b,option_c,option_d,explanation\n"
            "What is H2O?,short,Water,,,,, Water is H2O\n"
            "Is the sky blue?,truefalse,True,,,,, Yes it is\n",
            encoding="utf-8",
        )
        count, errors = quiz_service.import_from_csv(quiz.id, str(csv_file))
        assert count == 2
        assert errors == []

    def test_csv_import_missing_column(self, quiz_service, tmp_path):
        quiz = quiz_service.create("Bad CSV")
        bad_file = tmp_path / "bad.csv"
        bad_file.write_text("question,option_a\nQ,A\n")
        count, errors = quiz_service.import_from_csv(quiz.id, str(bad_file))
        assert count == 0
        assert any("correct_answer" in e for e in errors)

    def test_csv_import_missing_file(self, quiz_service):
        quiz = quiz_service.create("Ghost")
        count, errors = quiz_service.import_from_csv(quiz.id, "/nonexistent/path.csv")
        assert count == 0
        assert len(errors) > 0

    def test_ai_generate_mocked(self, quiz_service, mocker):
        """AI generation should parse JSON array from Claude response."""
        fake_response_text = (
            '[{"question": "Q1?", "correct_answer": "A1", '
            '"option_a": "", "option_b": "", "option_c": "", "option_d": "", '
            '"explanation": "Exp1"}]'
        )
        # Mock out the anthropic client
        mock_msg = mocker.MagicMock()
        mock_msg.content[0].text = fake_response_text
        mock_client = mocker.MagicMock()
        mock_client.messages.create.return_value = mock_msg
        mocker.patch("anthropic.Anthropic", return_value=mock_client)

        questions = quiz_service.generate_with_ai("fake-key", "History", 1, "short")
        assert len(questions) == 1
        assert questions[0]["question"] == "Q1?"
