from utils.ocr_utils import merge_adjacent_words


def test_merge_adjacent_words_groups_neighboring_words_on_same_line():
    words = [
        {"text": "hello", "confidence": 90, "box": {"x": 10, "y": 10, "w": 20, "h": 10}},
        {"text": "world", "confidence": 80, "box": {"x": 35, "y": 11, "w": 25, "h": 10}},
        {"text": "next", "confidence": 70, "box": {"x": 10, "y": 40, "w": 20, "h": 10}},
    ]

    merged = merge_adjacent_words(words)

    assert len(merged) == 2
    assert merged[0]["text"] == "hello world"
    assert merged[0]["box"] == {"x": 10, "y": 10, "w": 50, "h": 11}
    assert merged[1]["text"] == "next"

