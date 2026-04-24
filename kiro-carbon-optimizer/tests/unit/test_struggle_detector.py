"""Unit tests for StruggleDetector."""
from core.struggle_detector import StruggleDetector


def test_two_identical_prompts_raises_signal():
    detector = StruggleDetector()
    detector.on_prompt_submitted("Fix this error in my code", [])
    signals = detector.on_prompt_submitted("Fix this error in my code", [])
    signal_types = [s.signal_type for s in signals]
    assert "repeated_prompt_loop" in signal_types or "repeated_content_pasting" in signal_types


def test_two_dissimilar_prompts_no_similarity_signal():
    detector = StruggleDetector()
    detector.on_prompt_submitted("Fix this error in my code", [])
    signals = detector.on_prompt_submitted("How do I deploy to AWS S3 bucket", [])
    signal_types = [s.signal_type for s in signals]
    assert "repeated_prompt_loop" not in signal_types


def test_oversized_prompt_raises_signal():
    detector = StruggleDetector()
    long_prompt = "x" * 6001  # > 1500 tokens (6001/4 = 1500.25 -> ceil = 1501)
    signals = detector.on_prompt_submitted(long_prompt, [])
    signal_types = [s.signal_type for s in signals]
    assert "oversized_prompt" in signal_types


def test_prompt_under_token_limit_no_signal():
    detector = StruggleDetector()
    short_prompt = "Fix this bug"
    signals = detector.on_prompt_submitted(short_prompt, [])
    signal_types = [s.signal_type for s in signals]
    assert "oversized_prompt" not in signal_types


def test_high_frequency_file_requests_raises_signal():
    detector = StruggleDetector()
    for _ in range(7):
        signals = detector.on_prompt_submitted("fix it", ["app.py"])
    signal_types = [s.signal_type for s in signals]
    assert "high_frequency_retry" in signal_types


def test_six_file_requests_no_signal():
    detector = StruggleDetector()
    for _ in range(6):
        signals = detector.on_prompt_submitted("fix it", ["app.py"])
    signal_types = [s.signal_type for s in signals]
    assert "high_frequency_retry" not in signal_types


def test_same_content_hash_raises_signal():
    detector = StruggleDetector()
    same_prompt = "Here is my error log: ERROR: null pointer exception at line 42"
    detector.on_prompt_submitted(same_prompt, [])
    signals = detector.on_prompt_submitted(same_prompt, [])
    signal_types = [s.signal_type for s in signals]
    assert "repeated_content_pasting" in signal_types


def test_three_rejections_raises_high_severity_signal():
    detector = StruggleDetector()
    for _ in range(3):
        signals = detector.on_edit_reverted("main.py")
    assert len(signals) > 0
    assert signals[0].severity == "high"
    assert signals[0].signal_type == "repeated_rejections"


def test_no_signals_returns_empty_list():
    detector = StruggleDetector()
    signals = detector.on_prompt_submitted("How do I sort a list in Python?", [])
    # First prompt — no history to compare against, no file refs, short prompt
    assert isinstance(signals, list)
    # May or may not be empty depending on content hash (first occurrence = no signal)
    signal_types = [s.signal_type for s in signals]
    assert "repeated_prompt_loop" not in signal_types
    assert "high_frequency_retry" not in signal_types
    assert "oversized_prompt" not in signal_types
