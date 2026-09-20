"""Tests for Notebook.find_tab_root page resolution under GTK4."""

import os
import sys

import gi

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
gi.require_version("Gtk", "4.0")

from gi.repository import Gtk

from terminatorlib.notebook import Notebook


class FakeNotebook(Gtk.Notebook):
    """A bare Gtk.Notebook borrowing Notebook's find_tab_root."""

    find_tab_root = Notebook.find_tab_root


def make_notebook(pages):
    notebook = FakeNotebook()
    for page in pages:
        notebook.append_page(page, Gtk.Label(label="tab"))
    # realize the hierarchy so GTK4 interposes its internal GtkStack
    window = Gtk.Window()
    window.set_child(notebook)
    return notebook


def test_find_tab_root_returns_the_page_itself():
    page = Gtk.Label(label="page")
    notebook = make_notebook([page])

    assert notebook.find_tab_root(page) is page


def test_find_tab_root_resolves_a_nested_widget_to_its_page():
    inner = Gtk.Label(label="inner")
    box = Gtk.Box()
    box.append(inner)
    page = Gtk.Box()
    page.append(box)
    notebook = make_notebook([page])

    assert notebook.find_tab_root(inner) is page


def test_find_tab_root_picks_the_correct_page_among_several():
    first = Gtk.Label(label="first")
    second_inner = Gtk.Label(label="second inner")
    second = Gtk.Box()
    second.append(second_inner)
    notebook = make_notebook([first, second])

    assert notebook.find_tab_root(second_inner) is second
    assert notebook.page_num(notebook.find_tab_root(second_inner)) == 1


def test_find_tab_root_result_is_always_a_page_of_the_notebook():
    """The GTK4 regression: the internal GtkStack must never be returned."""
    inner = Gtk.Label(label="inner")
    page = Gtk.Box()
    page.append(inner)
    notebook = make_notebook([page])

    root = notebook.find_tab_root(inner)

    assert notebook.page_num(root) != -1
    assert not isinstance(root, Gtk.Stack)
