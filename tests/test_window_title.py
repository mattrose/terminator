"""Tests for top-level window title handling."""

import os
import sys

import gi

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
gi.require_version("Gtk", "3.0")

from terminatorlib.window import WindowTitle


class FakeWindow:
    """Record titles passed to the native window."""

    def __init__(self):
        self.titles = []

    def set_title(self, title):
        self.titles.append(title)


class FakeVte:
    """Expose the focus state used by WindowTitle."""

    def __init__(self, focused):
        self.focused = focused

    def is_focus(self):
        return self.focused


class FakeTerminal:
    """Provide the VTE widget associated with a title change."""

    def __init__(self, focused):
        self.vte = FakeVte(focused)

    def get_vte(self):
        return self.vte


def test_background_terminal_cannot_override_window_title():
    """Only the terminal owning focus should control the desktop title."""
    window = FakeWindow()
    title = WindowTitle(window)

    title.set_title(FakeTerminal(focused=True), "focused terminal")
    title.set_title(FakeTerminal(focused=False), "background terminal")

    assert title.text == "focused terminal"
    assert window.titles == ["focused terminal"]
