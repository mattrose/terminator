# Plugin by Sinan Nalkaya <sardok@gmail.com>
# See LICENSE of Terminator package.

""" logger.py - Terminator Plugin to log 'content' of individual
terminals """

import os
import sys
from gi.repository import Gtk, Vte, GLib
import terminatorlib.plugin as plugin
from terminatorlib.translation import _

AVAILABLE = ['Logger']

class Logger(plugin.MenuItem):
    """ Add custom command to the terminal menu"""
    capabilities = ['terminal_menu']
    loggers = None
    dialog_action = Gtk.FileChooserAction.SAVE
    vte_version = Vte.get_minor_version()

    def __init__(self):
        plugin.MenuItem.__init__(self)
        if not self.loggers:
            self.loggers = {}

    def callback(self, menuitems, menu, terminal):
        """ Add save menu item to the menu"""
        vte_terminal = terminal.get_vte()
        if vte_terminal not in self.loggers:
            menuitems.append((_('Start Logger'), self.start_logger, terminal))
        else:
            menuitems.append((_('Stop Logger'), self.stop_logger, terminal))

    def write_content(self, terminal, row_start, col_start, row_end, col_end):
        """ Final function to write a file """
        if self.vte_version < 72:
            content = terminal.get_text_range(row_start, col_start, row_end, col_end,
                                          lambda *a: True)
        else:
            content = terminal.get_text_range_format(Vte.Format.TEXT, row_start, col_start, row_end, col_end)
        content = content[0]
        fd = self.loggers[terminal]["fd"]
        fd.write(content[:-1])
        self.loggers[terminal]["col"] = col_end
        self.loggers[terminal]["row"] = row_end

    def save(self, terminal):
        """ 'contents-changed' callback """
        last_saved_col = self.loggers[terminal]["col"]
        last_saved_row = self.loggers[terminal]["row"]
        (col, row) = terminal.get_cursor_position()
        if row - last_saved_row < terminal.get_row_count():
            return
        self.write_content(terminal, last_saved_row, last_saved_col, row, col)

    def start_logger(self, _widget, terminal):
        """ Handle menu item callback by saving text to a file"""
        savedialog = Gtk.FileChooserDialog(
            title=_("Save Log File As"),
            transient_for=terminal.get_root(),
            action=self.dialog_action
        )
        savedialog.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        savedialog.add_button(_("_Save"), Gtk.ResponseType.OK)
        savedialog.set_do_overwrite_confirmation(True)
        savedialog.set_local_only(True)

        result = [Gtk.ResponseType.CANCEL]
        logfile = [None]
        loop = GLib.MainLoop()

        def on_response(d, r):
            result[0] = r
            if r == Gtk.ResponseType.OK:
                gfile = d.get_file()
                if gfile:
                    logfile[0] = gfile.get_path()
            d.destroy()
            loop.quit()

        savedialog.connect('response', on_response)
        savedialog.present()
        loop.run()

        if result[0] == Gtk.ResponseType.OK and logfile[0]:
            try:
                fd = open(logfile[0], 'w+')
                vte_terminal = terminal.get_vte()
                (col, row) = vte_terminal.get_cursor_position()
                self.loggers[vte_terminal] = {"filepath": logfile[0],
                                              "handler_id": 0, "fd": fd,
                                              "col": col, "row": row}
                self.loggers[vte_terminal]["handler_id"] = vte_terminal.connect('contents-changed', self.save)
            except Exception as ex:
                error = Gtk.MessageDialog(
                    transient_for=terminal.get_root(),
                    modal=True,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=str(ex)
                )
                err_loop = GLib.MainLoop()
                error.connect('response', lambda d, r: (d.destroy(), err_loop.quit()))
                error.present()
                err_loop.run()

    def stop_logger(self, _widget, terminal):
        vte_terminal = terminal.get_vte()
        last_saved_col = self.loggers[vte_terminal]["col"]
        last_saved_row = self.loggers[vte_terminal]["row"]
        (col, row) = vte_terminal.get_cursor_position()
        if last_saved_col != col or last_saved_row != row:
            self.write_content(vte_terminal, last_saved_row, last_saved_col, row, col)
        fd = self.loggers[vte_terminal]["fd"]
        fd.close()
        vte_terminal.disconnect(self.loggers[vte_terminal]["handler_id"])
        del(self.loggers[vte_terminal])
