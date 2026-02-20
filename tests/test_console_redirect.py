"""Тесты редиректа stdout/stderr и удаления ANSI-последовательностей."""
import pytest

from app.console_redirect import strip_ansi


class TestStripAnsi:
    """Удаление ANSI escape-последовательностей из строки."""

    def test_empty_string(self) -> None:
        assert strip_ansi("") == ""

    def test_plain_text_unchanged(self) -> None:
        assert strip_ansi("hello") == "hello"
        assert strip_ansi("Epoch 1/50") == "Epoch 1/50"

    def test_strips_escape_sequences(self) -> None:
        # типичные последовательности: цвет, сброс, erase to end of line
        assert strip_ansi("foo\x1b[0m bar") == "foo bar"
        assert strip_ansi("\x1b[31mred\x1b[0m") == "red"
        assert strip_ansi("line\x1b[K") == "line"

    def test_strips_complex_sequence(self) -> None:
        s = "\x1b[1;32mbold green\x1b[0m"
        assert strip_ansi(s) == "bold green"


class TestStdoutStderrRedirect:
    def test_nested_redirect_restore_is_safe(self, monkeypatch):
        import sys
        from queue import Queue
        from app.console_redirect import redirect_stdout_stderr_to_queue, restore_stdout_stderr

        q1, q2 = Queue(), Queue()
        orig_out, orig_err = sys.stdout, sys.stderr

        o1, e1 = redirect_stdout_stderr_to_queue(q1, also_keep_original=False)
        assert sys.stdout is not orig_out
        o2, e2 = redirect_stdout_stderr_to_queue(q2, also_keep_original=False)
        assert sys.stdout is not orig_out
        # Restore inner
        restore_stdout_stderr(o2, e2)
        # After restoring inner, we should be back to the first redirected writer (not original yet)
        assert sys.stdout is not orig_out
        # Restore outer
        restore_stdout_stderr(o1, e1)
        assert sys.stdout is orig_out
        assert sys.stderr is orig_err
