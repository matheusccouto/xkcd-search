"""Pytest terminal reporting for retrieval benchmarks."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.terminal import TerminalReporter


def pytest_terminal_summary(terminalreporter: TerminalReporter) -> None:
    """Print retrieval metrics report at the end of the pytest session."""
    reports_passed = terminalreporter.getreports("passed")
    reports_failed = terminalreporter.getreports("failed")
    reports = reports_passed + reports_failed

    ranks = [
        val
        for reports in reports
        for key, val in reports.user_properties
        if key == "rank"
    ]

    if not ranks:
        return

    total = len(ranks)
    h1 = sum(r == 1 for r in ranks)
    h5 = sum(0 < r <= 5 for r in ranks)
    mrr = sum((1.0 / r if r > 0 else 0.0) for r in ranks) / total

    terminalreporter.section("Retrieval Benchmark Report", sep="=")
    terminalreporter.line(f"Total Cases: {total}")
    terminalreporter.line(f"Hit@1: {h1}/{total} ({(h1 / total) * 100:.1f}%)")
    terminalreporter.line(f"Hit@5: {h5}/{total} ({(h5 / total) * 100:.1f}%)")
    terminalreporter.line(f"MRR:   {mrr:.3f}")
