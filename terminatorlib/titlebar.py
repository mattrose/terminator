# Terminator by Chris Jones <cmsj@tenshu.net>
# GPL v2 only
"""titlebar.py - classes necessary to provide a terminal title bar"""

from gi.repository import Gtk, Gdk
from gi.repository import GObject
from gi.repository import Pango

from .version import APP_NAME
from .util import dbg
from .terminator import Terminator
from .editablelabel import EditableLabel
from .translation import _

# pylint: disable-msg=R0904
# pylint: disable-msg=W0613
class Titlebar(Gtk.Box):
    """Class implementing the Titlebar widget"""

    terminator = None
    terminal = None
    config = None
    oldtitle = None
    termtext = None
    sizetext = None
    label = None
    ebox = None
    groupicon = None
    grouplabel = None
    groupentry = None
    bellicon = None

    _self_bg_provider = None
    _ebox_bg_provider = None
    _grouplabel_fg_provider = None
    _grouplabel_font_attrs = None

    __gsignals__ = {
            'clicked': (GObject.SignalFlags.RUN_LAST, None, ()),
            'edit-done': (GObject.SignalFlags.RUN_LAST, None, ()),
            'create-group': (GObject.SignalFlags.RUN_LAST, None,
                (GObject.TYPE_STRING,)),
    }

    def __init__(self, terminal):
        """Class initialiser"""
        GObject.GObject.__init__(self)

        self.terminator = Terminator()
        self.terminal = terminal
        self.config = self.terminal.config

        self.label = EditableLabel()
        self.label.connect('edit-done', self.on_edit_done)
        self.ebox = Gtk.Box()
        grouphbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.grouplabel = Gtk.Label(ellipsize='end')
        self.groupicon = Gtk.Image()
        self.bellicon = Gtk.Image()
        self.bellicon.set_visible(False)

        self.groupentry = Gtk.Entry()
        self.groupentry.set_visible(False)

        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect('leave', lambda c: self.groupentry_cancel())
        self.groupentry.add_controller(focus_ctrl)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect('key-pressed', self._groupentry_key_pressed)
        self.groupentry.add_controller(key_ctrl)

        self.groupentry.connect('activate', self.groupentry_activate)

        groupsend_type = self.terminator.groupsend_type
        if self.terminator.groupsend == groupsend_type['all']:
            icon_name = 'all'
        elif self.terminator.groupsend == groupsend_type['group']:
            icon_name = 'group'
        elif self.terminator.groupsend == groupsend_type['off']:
            icon_name = 'off'
        self.set_from_icon_name('_active_broadcast_%s' % icon_name)

        grouphbox.append(self.groupicon)
        self.groupicon.set_margin_start(2)
        self.groupicon.set_margin_end(2)
        grouphbox.append(self.grouplabel)
        self.grouplabel.set_margin_start(2)
        self.grouplabel.set_margin_end(2)
        grouphbox.append(self.groupentry)
        self.groupentry.set_margin_start(2)
        self.groupentry.set_margin_end(2)

        self.ebox.append(grouphbox)

        self.bellicon.set_from_icon_name('terminal-bell')

        viewport = Gtk.Viewport(hscroll_policy='natural')
        viewport.set_child(self.label)
        viewport.set_hexpand(True)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.append(self.ebox)
        hbox.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        hbox.append(viewport)
        self.bellicon.set_margin_start(2)
        self.bellicon.set_margin_end(2)
        hbox.append(self.bellicon)

        self.append(hbox)

        gesture = Gtk.GestureClick()
        gesture.connect('pressed', self.on_clicked)
        self.add_controller(gesture)

    def _set_widget_bg(self, widget, color_str, attr):
        """Apply a background color to a widget via CSS"""
        provider = getattr(self, attr)
        if provider is None:
            provider = Gtk.CssProvider()
            setattr(self, attr, provider)
            widget.get_style_context().add_provider(
                provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        provider.load_from_data(
            ("* { background-color: %s; }" % color_str).encode())

    def _set_grouplabel_fg(self, color_str):
        """Apply a foreground color to grouplabel via CSS"""
        if self._grouplabel_fg_provider is None:
            self._grouplabel_fg_provider = Gtk.CssProvider()
            self.grouplabel.get_style_context().add_provider(
                self._grouplabel_fg_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._grouplabel_fg_provider.load_from_data(
            ("label { color: %s; }" % color_str).encode())

    def connect_icon(self, func):
        """Connect the supplied function to clicking on the group icon"""
        gesture = Gtk.GestureClick()
        gesture.connect('pressed', func)
        self.ebox.add_controller(gesture)

    def update(self, other=None):
        """Update our contents"""
        default_bg = False

        temp_heldtext_str = ''
        temp_sizetext_str = ''

        if self.terminal.is_held_open:
            temp_heldtext_str = _('[INACTIVE: Right-Click for Relaunch option] ')
        if not self.config['title_hide_sizetext']:
            temp_sizetext_str = " %s" % (self.sizetext)
        self.label.set_text("%s%s%s" % (temp_heldtext_str, self.termtext, temp_sizetext_str))

        if (not self.config['title_use_system_font']) and self.config['title_font']:
            title_font = Pango.FontDescription(self.config['title_font'])
        else:
            title_font = Pango.FontDescription(self.config.get_system_prop_font())
        self.label.modify_font(title_font)
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_font_desc_new(title_font))
        self.grouplabel.set_attributes(attrs)

        if other:
            term = self.terminal
            terminator = self.terminator
            if other == 'window-focus-out':
                title_fg = self.config['title_inactive_fg_color']
                title_bg = self.config['title_inactive_bg_color']
                icon = '_receive_off'
                default_bg = True
                group_fg = self.config['title_inactive_fg_color']
                group_bg = self.config['title_inactive_bg_color']
            elif term != other and term.group and term.group == other.group:
                if terminator.groupsend == terminator.groupsend_type['off']:
                    title_fg = self.config['title_inactive_fg_color']
                    title_bg = self.config['title_inactive_bg_color']
                    icon = '_receive_off'
                    default_bg = True
                else:
                    title_fg = self.config['title_receive_fg_color']
                    title_bg = self.config['title_receive_bg_color']
                    icon = '_receive_on'
                group_fg = self.config['title_receive_fg_color']
                group_bg = self.config['title_receive_bg_color']
            elif term != other and not term.group or term.group != other.group:
                if terminator.groupsend == terminator.groupsend_type['all']:
                    title_fg = self.config['title_receive_fg_color']
                    title_bg = self.config['title_receive_bg_color']
                    icon = '_receive_on'
                else:
                    title_fg = self.config['title_inactive_fg_color']
                    title_bg = self.config['title_inactive_bg_color']
                    icon = '_receive_off'
                    default_bg = True
                group_fg = self.config['title_inactive_fg_color']
                group_bg = self.config['title_inactive_bg_color']
            else:
                # We're the active terminal
                title_fg = self.config['title_transmit_fg_color']
                title_bg = self.config['title_transmit_bg_color']
                if terminator.groupsend == terminator.groupsend_type['all']:
                    icon = '_active_broadcast_all'
                elif terminator.groupsend == terminator.groupsend_type['group']:
                    icon = '_active_broadcast_group'
                else:
                    icon = '_active_broadcast_off'
                group_fg = self.config['title_transmit_fg_color']
                group_bg = self.config['title_transmit_bg_color']

            rgba = Gdk.RGBA()
            rgba.parse(title_fg)
            self.label.modify_fg(None, rgba)
            self._set_grouplabel_fg(group_fg)
            if not self.get_desired_visibility():
                title_bg = title_bg if not default_bg else '#000000'
            self._set_widget_bg(self, title_bg, '_self_bg_provider')
            self.update_visibility()
            self._set_widget_bg(self.ebox, group_bg, '_ebox_bg_provider')
            self.set_from_icon_name(icon)

    def update_visibility(self):
        """Make the titlebar be visible or not"""
        if not self.get_desired_visibility():
            dbg('hiding titlebar')
            self.hide()
            self.label.hide()
        else:
            dbg('showing titlebar')
            self.show()
            self.label.show()

    def get_desired_visibility(self):
        """Returns True if the titlebar is supposed to be visible. False if
        not"""
        if self.editing() == True or self.terminal.group:
            dbg('implicit desired visibility')
            return(True)
        else:
            dbg('configured visibility: %s' % self.config['show_titlebar'])
            return(self.config['show_titlebar'])

    def set_from_icon_name(self, name, size=None):
        """Set an icon for the group label"""
        if not name:
            self.groupicon.hide()
            return

        self.groupicon.set_from_icon_name(APP_NAME + name)
        self.groupicon.show()

    def update_terminal_size(self, width, height):
        """Update the displayed terminal size"""
        self.sizetext = "%sx%s" % (width, height)
        self.update()

    def set_terminal_title(self, widget, title):
        """Update the terminal title"""
        self.termtext = title
        self.update()
        # Return False so we don't interrupt any chains of signal handling
        return False

    def set_group_label(self, name):
        """Set the name of the group"""
        if name:
            self.grouplabel.set_text(name)
            self.grouplabel.show()
        else:
            self.grouplabel.set_text('')
            self.grouplabel.hide()
        self.update_visibility()

    def on_clicked(self, gesture, n_press, x, y):
        """Handle a click on the label"""
        self.set_visible(True)
        self.label.set_visible(True)
        self.emit('clicked')

    def on_edit_done(self, widget):
        """Re-emit an edit-done signal from an EditableLabel"""
        self.emit('edit-done')

    def editing(self):
        """Determine if we're currently editing a group name or title"""
        return(self.groupentry.get_visible() or self.label.editing())

    def create_group(self):
        """Create a new group"""
        if self.terminal.group:
            self.groupentry.set_text(self.terminal.group)
        else:
            self.groupentry.set_text(self.terminator.new_random_group())
        self.groupentry.show()
        self.grouplabel.hide()
        self.groupentry.grab_focus()
        self.update_visibility()

    def groupentry_cancel(self, *args):
        """Hide the group name entry"""
        self.groupentry.set_text('')
        self.groupentry.hide()
        self.grouplabel.show()
        self.get_parent().grab_focus()

    def groupentry_activate(self, widget):
        """Actually cause a group to be created"""
        groupname = self.groupentry.get_text() or None
        dbg('creating group: %s' % groupname)
        self.groupentry_cancel()
        last_focused_term = self.terminator.last_focused_term
        if self.terminal.targets_for_new_group:
            [term.titlebar.emit('create-group', groupname) for term in self.terminal.targets_for_new_group]
            self.terminal.targets_for_new_group = None
        else:
            self.emit('create-group', groupname)
        last_focused_term.grab_focus()
        self.terminator.focus_changed(last_focused_term)

    def _groupentry_key_pressed(self, ctrl, keyval, keycode, state):
        """Handle keypresses on the entry widget"""
        key = Gdk.keyval_name(keyval)
        if key == 'Escape':
            self.groupentry_cancel()

    def icon_bell(self):
        """A bell signal requires we display our bell icon"""
        self.bellicon.show()
        GObject.timeout_add(1000, self.icon_bell_hide)

    def icon_bell_hide(self):
        """Handle a timeout which means we now hide the bell icon"""
        self.bellicon.hide()
        return(False)

    def get_custom_string(self):
        """If we have a custom string set, return it, otherwise None"""
        if self.label.is_custom():
            return(self.label.get_text())
        else:
            return(None)

    def set_custom_string(self, string):
        """Set a custom string"""
        self.label.set_text(string)
        self.label.set_custom()

GObject.type_register(Titlebar)
