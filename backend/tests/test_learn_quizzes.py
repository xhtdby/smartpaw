import json
from pathlib import Path


QUIZ_PATH = Path(__file__).resolve().parents[1] / "data" / "learn_quizzes.json"
LANGUAGES = {"en", "hi", "mr"}


def test_learn_quiz_json_shape_is_grounded_and_trilingual():
    data = json.loads(QUIZ_PATH.read_text(encoding="utf-8"))

    assert data
    for topic_id, questions in data.items():
        assert topic_id
        assert isinstance(questions, list)
        assert questions
        for question in questions:
            assert question["source_entry_id"]
            assert set(question["q"]) == LANGUAGES
            assert set(question["options"]) == LANGUAGES
            assert set(question["explanation"]) == LANGUAGES
            for language in LANGUAGES:
                options = question["options"][language]
                assert len(options) >= 3
                assert all(option.strip() for option in options)
                assert question["q"][language].strip()
                assert question["explanation"][language].strip()
                assert 0 <= question["correct_index"] < len(options)


def test_quiz_topics_cover_learn_and_first_aid_entry_points():
    data = json.loads(QUIZ_PATH.read_text(encoding="utf-8"))

    required_topics = {
        "approach",
        "trauma",
        "heat",
        "poison",
        "skin",
        "puppies",
        "bleeding",
        "choking",
        "wound-cleaning",
        "fracture",
        "dehydration",
        "otc-medicine",
    }

    assert required_topics.issubset(data.keys())
