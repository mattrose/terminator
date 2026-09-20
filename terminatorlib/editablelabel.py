# vim: tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#
# Copyright (c) 2009, Emmanuel Bretelle <chantra@debuntu.org>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 only.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor
#    , Boston, MA  02110-1301  USA

""" Editable Label class"""
from gi.repository import GLib, GObject, Gtk, Gdk, Pango

class EditableLabel(Gtk.Box):
    # pylint: disable-msg=W0212
    # pylint: disable-msg=R0904
    """
    A box that partially emulates a Gtk.Label.
    On double-click or key binding the label is editable; entering an empty
    string reverts back to automatic text.
    """
    _label = None
    _autotext = None
    _custom = None
    _entry = None
    _entry_controllers = None
    _fg_provider = None

    __gsignals__ = {
            'edit-done': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, text=""):
        GObject.GObject.__init__(self)

        self._entry_controllers = []
        self._label = Gtk.Label(label=text, ellipsize='end')
        self._custom = False
        self.append(self._label)

        gesture = Gtk.GestureClick()
        gesture.set_button(1)
        gesture.connect('pressed', self._on_click_text)
        self.add_controller(gesture)

    def set_angle(self, angle):
        """set angle of the label (no-op in GTK4, label rotation removed)"""
        pass

    def editing(self):
        """Return if we are currently editing"""
        return self._entry is not None

    def set_text(self, text, force=False):
        """set the text of the label"""
        self._autotext = text
        if not self._custom or force:
            self._label.set_text(text)

    def get_text(self):
        """get the text from the label"""
        return self._label.get_text()

    def edit(self):
        """Start editing the widget text"""
        if self._entry:
            return False
        self.remove(self._label)
        self._entry = Gtk.Entry()
        self._entry.set_text(self._label.get_text())
        self.append(self._entry)

        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect('leave', self._on_entry_focus_leave)
        self._entry.add_controller(focus_ctrl)
        self._entry_controllers.append(focus_ctrl)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect('key-pressed', self._on_entry_keypress)
        self._entry.add_controller(key_ctrl)
        self._entry_controllers.append(key_ctrl)

        btn_gesture = Gtk.GestureClick()
        btn_gesture.set_button(3)
        btn_gesture.connect('pressed', self._on_entry_buttonpress)
        self._entry.add_controller(btn_gesture)
        self._entry_controllers.append(btn_gesture)

        self._entry.connect('activate', self._on_entry_activated)
        self._entry.grab_focus()

    def _on_click_text(self, gesture, n_press, x, y):
        if n_press == 2:
            self.edit()
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _entry_to_label(self):
        """Replace Gtk.Entry with Gtk.Label"""
        if self._entry and self._entry is self.get_first_child():
            self._entry_controllers = []
            self.remove(self._entry)
            self._entry = None
            self.append(self._label)
            self.emit('edit-done')
            return True
        return False

    def _on_entry_focus_leave(self, ctrl):
        self._entry_to_label()

    def _on_entry_activated(self, widget):
        """Get the text entered in Gtk.Entry"""
        entry = self._entry.get_text()
        label = self._label.get_text()
        if entry == '':
            self._custom = False
            self.set_text(self._autotext)
        elif entry != label:
            self._custom = True
            self._label.set_text(entry)
        self._entry_to_label()

    def _on_entry_keypress(self, ctrl, keyval, keycode, state):
        """Handle keypresses in Gtk.Entry"""
        key = Gdk.keyval_name(keyval)
        if key == 'Escape':
            self._entry_to_label()

    def _on_entry_buttonpress(self, gesture, n_press, x, y):
        """Block right-click context menu to avoid deadlock"""
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def modify_fg(self, state, color):
        """Set the label foreground color"""
        if color is None:
            if self._fg_provider:
                self._label.get_style_context().remove_provider(self._fg_provider)
                self._fg_provider = None
            return
        if hasattr(color, 'to_string'):
            css = "* { color: %s; }" % color.to_string()
        else:
            return
        if self._fg_provider is None:
            self._fg_provider = Gtk.CssProvider()
            self._label.get_style_context().add_provider(
                self._fg_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._fg_provider.load_from_data(css.encode())

    def is_custom(self):
        """Return whether or not we have a custom string set"""
        return self._custom

    def set_custom(self):
        """Set the customness of the string to True"""
        self._custom = True

    def modify_font(self, fontdesc):
        """Set the label font using a Pango.FontDescription"""
        if fontdesc:
            attrs = Pango.AttrList()
            attrs.insert(Pango.attr_font_desc_new(fontdesc))
            self._label.set_attributes(attrs)

GObject.type_register(EditableLabel)
