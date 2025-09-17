#!/usr/bin/env python3
"""Utility script for inspecting automatic heading numbering."""

from core.numbering.auto_numberer import AutoNumberer


def run_demo() -> None:
    """Print a sample numbering sequence produced by :class:`AutoNumberer`."""
    print("Testing automatic numbering system:")
    print("=" * 50)

    numberer = AutoNumberer()

    # Test sequence that should produce: 1, 1.1, 1.2, 1.2.1, 1.2.2, 1.3, 2, 2.1
    test_levels = [1, 2, 2, 3, 3, 2, 1, 2]
    expected = ["1", "1.1", "1.2", "1.2.1", "1.2.2", "1.3", "2", "2.1"]

    print("Testing numbering sequence:")
    for level, expected_num in zip(test_levels, expected):
        number = numberer.get_number_for_level(level)
        status = "✓" if number == expected_num else "✗"
        print(f"  H{level} -> {number} (expected {expected_num}) {status}")


if __name__ == "__main__":
    run_demo()
