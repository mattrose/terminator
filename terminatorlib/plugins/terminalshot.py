# Terminator by Chris Jones <cmsj@tenshu.net>
# GPL v2 only
"""terminalshot.py - Terminator Plugin to take 'screenshots' of individual
terminals"""

import os
from gi.repository import Gtk, GLib
import terminatorlib.plugin as plugin
from terminatorlib.translation import _
from terminatorlib.util import widget_pixbuf

AVAILABLE = ['TerminalShot']

class TerminalShot(plugin.MenuItem):
    """Add custom commands to the terminal menu"""
    capabilities = ['terminal_menu']
    dialog_action = Gtk.FileChooserAction.SAVE

    def __init__(self):
        plugin.MenuItem.__init__(self)

    def callback(self, menuitems, menu, terminal):
        """Add our menu items to the menu"""
        menuitems.append((_('Terminal screenshot'), self.terminalshot, terminal))

    def terminalshot(self, _widget, terminal):
        """Handle the taking, prompting and saving of a terminalshot"""
        orig_pixbuf = widget_pixbuf(terminal)

        savedialog = Gtk.FileChooserDialog(
            title=_("Save image"),
            transient_for=terminal.get_root(),
            action=self.dialog_action
        )
        savedialog.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        savedialog.add_button(_("_Save"), Gtk.ResponseType.OK)
        savedialog.set_do_overwrite_confirmation(True)
        savedialog.set_local_only(True)

        result = [Gtk.ResponseType.CANCEL]
        path = [None]
        loop = GLib.MainLoop()

        def on_response(d, r):
            result[0] = r
            if r == Gtk.ResponseType.OK:
                gfile = d.get_file()
                if gfile:
                    path[0] = gfile.get_path()
            d.destroy()
            loop.quit()

        savedialog.connect('response', on_response)
        savedialog.present()
        loop.run()

        if result[0] == Gtk.ResponseType.OK and path[0] and orig_pixbuf:
            orig_pixbuf.savev(path[0], 'png', [], [])
