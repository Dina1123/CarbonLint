"""Unit tests for DiffTracker."""
from core.diff_tracker import DiffTracker


def test_three_overlapping_edits_returns_true():
    tracker = DiffTracker()
    tracker.record_edit("app.py", (10, 20))
    tracker.record_edit("app.py", (15, 25))
    tracker.record_edit("app.py", (12, 18))
    assert tracker.check_repeated_region("app.py", (10, 20)) is True


def test_two_overlapping_edits_returns_false():
    tracker = DiffTracker()
    tracker.record_edit("app.py", (10, 20))
    tracker.record_edit("app.py", (15, 25))
    assert tracker.check_repeated_region("app.py", (10, 20)) is False


def test_non_overlapping_edits_returns_false():
    tracker = DiffTracker()
    tracker.record_edit("app.py", (1, 5))
    tracker.record_edit("app.py", (1, 5))
    tracker.record_edit("app.py", (1, 5))
    assert tracker.check_repeated_region("app.py", (50, 60)) is False


def test_different_files_not_counted():
    tracker = DiffTracker()
    tracker.record_edit("app.py", (10, 20))
    tracker.record_edit("app.py", (10, 20))
    tracker.record_edit("other.py", (10, 20))
    assert tracker.check_repeated_region("app.py", (10, 20)) is False
