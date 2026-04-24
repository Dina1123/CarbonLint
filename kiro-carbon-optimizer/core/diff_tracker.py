"""Tracks AI-generated file edits and detects repeated modifications to the same region."""
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class EditEvent:
    file_path: str
    line_range: Tuple[int, int]  # (start_line, end_line)


class DiffTracker:
    def __init__(self):
        self._edits: List[EditEvent] = []

    def record_edit(self, file_path: str, line_range: Tuple[int, int]) -> None:
        """Record an AI-generated edit event."""
        self._edits.append(EditEvent(file_path=file_path, line_range=line_range))

    def check_repeated_region(self, file_path: str, line_range: Tuple[int, int]) -> bool:
        """Return True if overlapping edits >= 3 for this file+region."""
        start, end = line_range
        count = 0
        for edit in self._edits:
            if edit.file_path != file_path:
                continue
            # Check overlap: two ranges overlap if start1 <= end2 AND start2 <= end1
            e_start, e_end = edit.line_range
            if start <= e_end and e_start <= end:
                count += 1
        return count >= 3
