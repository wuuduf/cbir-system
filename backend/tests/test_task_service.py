"""Tests for background task progress parsing."""

from app.services.task_service import TQDM_RE


def test_tqdm_progress_regex_matches_index_output() -> None:
    line = "build deep: 100%|██████████| 1875/1875 [00:58<00:00, 31.94it/s]"

    match = TQDM_RE.search(line)

    assert match is not None
    assert match.group("label") == "build deep"
    assert match.group("percent") == "100"
    assert match.group("current") == "1875"
    assert match.group("total") == "1875"
