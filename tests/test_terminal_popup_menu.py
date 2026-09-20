"""Tests for terminal context menu actions."""

import os
import sys

import gi

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from terminatorlib.terminal_popup_menu import TerminalPopupMenu


class FakeContainer:
    """Container recording confirmation requests."""

    def __init__(self, response, parent=None):
        self.response = response
        self.parent = parent
        self.confirmations = []

    def construct_confirm_close(self, window, child):
        self.confirmations.append((window, child))
        return self.response

    def get_parent(self):
        return self.parent


class FakeParent:
    """Intermediate widget without close confirmation behavior."""

    def __init__(self, parent):
        self.parent = parent

    def get_parent(self):
        return self.parent


class FakeTerminal:
    """Terminal recording close calls."""

    def __init__(self, parent=None, toplevel=None):
        self.parent = parent
        self.toplevel = toplevel
        self.closed = False

    def get_parent(self):
        return self.parent

    def get_root(self):
        return self.toplevel

    def close(self):
        self.closed = True


def popup_for(terminal):
    popup = TerminalPopupMenu.__new__(TerminalPopupMenu)
    popup.terminal = terminal
    return popup


def test_close_terminal_closes_after_confirmation_accepts():
    """Context menu close uses the container confirmation path."""
    window = object()
    container = FakeContainer(Gtk.ResponseType.ACCEPT)
    terminal = FakeTerminal(parent=container, toplevel=window)

    popup_for(terminal).close_terminal()

    assert terminal.closed
    assert container.confirmations == [(window, terminal)]


def test_close_terminal_keeps_terminal_open_when_confirmation_rejects():
    """A rejected confirmation prevents context menu close."""
    container = FakeContainer(Gtk.ResponseType.REJECT)
    terminal = FakeTerminal(parent=container, toplevel=object())

    popup_for(terminal).close_terminal()

    assert not terminal.closed
    assert container.confirmations == [(terminal.get_root(), terminal)]


def test_close_terminal_finds_confirmation_container_above_parent_widget():
    """Intermediate GTK widgets do not bypass close confirmation."""
    container = FakeContainer(Gtk.ResponseType.ACCEPT)
    parent = FakeParent(container)
    terminal = FakeTerminal(parent=parent, toplevel=object())

    popup_for(terminal).close_terminal()

    assert terminal.closed
    assert container.confirmations == [(terminal.get_root(), terminal)]
