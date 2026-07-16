import re
import os
import sys
import subprocess

from gi.repository import Gtk, GObject, GLib, Gdk

from terminatorlib.util import dbg
import terminatorlib.plugin as plugin
from terminatorlib.config import Config
from terminatorlib.translation import _
from terminatorlib.util import get_config_dir, err, dbg, gerr

(CC_COL_ENABLED, CC_COL_REGEXP, CC_COL_COMMAND) = list(range(0, 3))

AVAILABLE = ['RunCmdOnMatchMenu']

# For example, open scripts names outputted by python in Vim at the given line number:
# match = r'\B(/\S+?\.py)\S{2}\sline\s(\d+)' # Python's log file matching
# cmd = "gvim --servername IDE --remote +{1} {0}"

class RunCmdOnMatch(plugin.URLHandler):
    """Template for a class that run a command when a regexp match something printed on the terminal screen."""
    capabilities = ['url_handler']
    nameopen = "Open file"
    namecopy = "Copy file path"

    handler_name = None
    match = None
    cmd = None

    def callback(self, url):
        assert(self.__class__.match)
        assert(self.__class__.cmd)

        try:
            found = re.search(self.__class__.match, url)
        except Exception as e:
            dbg("ERROR while searching in the captured URL: {}".format(e))
            return None

        if not found:
            dbg("ERROR pattern not found")
            return None

        try:
            groups = found.groups()
            dbg("Groups: {}".format(groups))
        except Exception as e:
            dbg("ERROR while accessing groups: {}".format(e))
            return None

        for group in groups:
            if not group:
                dbg("ERROR groups not captured correctly: {groups}".format(groups=groups))
                return None

        try:
            runcmd = self.__class__.cmd.format(*groups)
        except Exception as e:
            err("Exception occurred while formatting the command: {} {}".format(type(e).__name__, e))

        dbg("run: {cmd}".format(cmd=runcmd))
        subprocess.run(runcmd.split())

        return "terminator://{cmd}".format(cmd=runcmd)


class MetaRCOM(type):
    """A meta-class for creating RunCmdOnMatch plugins on the fly."""
    def __new__(cls, name, regexp, cmd):
        return super().__new__(cls, name, (RunCmdOnMatch,), {"match": regexp, "cmd": cmd, "handler_name": name})


class RunCmdOnMatchMenu(plugin.MenuItem):
    """Add custom match/commands preference setting to the terminal menu"""
    capabilities = ['terminal_menu']
    cmd_list = {}
    conf_file = os.path.join(get_config_dir(), "run_cmd_on_match")

    def __init__(self):
        config = Config()
        sections = config.plugin_get_config(self.__class__.__name__)
        if not isinstance(sections, dict):
            return
        noord_cmds = []
        for part in sections:
            s = sections[part]
            if not ("regexp" in s and "command" in s):
                dbg("Ignoring section %s" % s)
                continue
            regexp = s["regexp"]
            command = s["command"]
            enabled = s["enabled"] and s["enabled"] or False
            if "position" in s:
                self.cmd_list[int(s["position"])] = {'enabled': enabled,
                                                     'regexp': regexp,
                                                     'command': command}
            else:
                noord_cmds.append({'enabled': enabled, 'regexp': regexp, 'command': command})
            for cmd in noord_cmds:
                self.cmd_list[len(self.cmd_list)] = cmd

            self._load_configured_handlers()

    def callback(self, menuitems, menu, terminal):
        """Add our menu items to the menu"""
        menuitems.append((_('Run command on matches'), [(_('Preferences'), self.configure)]))

    def _save_config(self):
        config = Config()
        config.plugin_del_config(self.__class__.__name__)
        i = 0
        for command in [self.cmd_list[key] for key in sorted(self.cmd_list.keys())]:
            enabled = command['enabled']
            regexp = command['regexp']
            cmd = command['command']

            item = {'enabled': enabled, 'regexp': regexp, 'command': cmd, 'position': i}
            config.plugin_set(self.__class__.__name__, regexp, item)
            i += 1
        config.save()
        self._load_configured_handlers()

    def _load_configured_handlers(self):
        """Forge an URLhandler plugin and hide it in the available ones."""
        me = sys.modules[__name__]
        config = Config()

        for key, handler in [(key, self.cmd_list[key]) for key in sorted(self.cmd_list.keys())]:
            rcom_name = "_RunCmdOnMatch_{}".format(key)
            RCOM = MetaRCOM(rcom_name, handler["regexp"], handler["command"])
            setattr(me, rcom_name, RCOM)

            if rcom_name not in AVAILABLE:
                AVAILABLE.append(rcom_name)
                dbg("add {} to the list of URL handlers: '{}' -> '{}'".format(rcom_name, RCOM.match, RCOM.cmd))

            if handler['enabled'] and rcom_name not in config["enabled_plugins"]:
                config["enabled_plugins"].append(rcom_name)

        config.save()

    def _execute(self, widget, data):
        command = data['command']
        if command[-1] != '\n':
            command = command + '\n'
        for terminal in data['terminals']:
            terminal.vte.feed_child(command.encode())

    def _run_dialog(self, dialog):
        """Run a dialog with GLib.MainLoop; return response code."""
        result = [Gtk.ResponseType.REJECT]
        loop = GLib.MainLoop()
        def on_response(d, r):
            result[0] = r
            loop.quit()
        dialog.connect('response', on_response)
        dialog.present()
        loop.run()
        return result[0]

    def _show_error(self, parent, text):
        err_dialog = Gtk.MessageDialog(
            transient_for=parent,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=text
        )
        loop = GLib.MainLoop()
        err_dialog.connect('response', lambda d, r: (d.destroy(), loop.quit()))
        err_dialog.present()
        loop.run()

    def configure(self, widget, data=None):
        ui = {}
        dbox = Gtk.Dialog(title=_("Run command on match Configuration"), modal=True)
        dbox.add_button(_("_Cancel"), Gtk.ResponseType.REJECT)
        dbox.add_button(_("_OK"), Gtk.ResponseType.ACCEPT)

        if widget and hasattr(widget, 'get_root'):
            dbox.set_transient_for(widget.get_root())

        try:
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            if icon_theme.has_icon('terminator-run-cmd-on-match'):
                dbox.set_icon_name('terminator-run-cmd-on-match')
        except Exception:
            dbg('Unable to load Terminator run-cmd-on-match icon')

        store = Gtk.ListStore(bool, str, str)
        for command in [self.cmd_list[key] for key in sorted(self.cmd_list.keys())]:
            store.append([command['enabled'], command['regexp'], command['command']])

        treeview = Gtk.TreeView(model=store)
        selection = treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)
        selection.connect("changed", self.on_selection_changed, ui)
        ui['treeview'] = treeview

        renderer = Gtk.CellRendererToggle()
        renderer.connect('toggled', self.on_toggled, ui)
        column = Gtk.TreeViewColumn(_("Enabled"), renderer, active=CC_COL_ENABLED)
        treeview.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("regexp"), renderer, text=CC_COL_REGEXP)
        treeview.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Command"), renderer, text=CC_COL_COMMAND)
        treeview.append_column(column)

        scroll_window = Gtk.ScrolledWindow()
        scroll_window.set_size_request(500, 250)
        scroll_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_window.set_child(treeview)

        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        scroll_window.set_hexpand(True)
        scroll_window.set_vexpand(True)
        main_hbox.append(scroll_window)

        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        def _btn(label, callback, sensitive=True):
            b = Gtk.Button(label=label)
            b.connect("clicked", callback, ui)
            b.set_sensitive(sensitive)
            button_box.append(b)
            return b

        ui['button_top'] = _btn(_("Top"), self.on_goto_top, False)
        ui['button_up'] = _btn(_("Up"), self.on_go_up, False)
        ui['button_down'] = _btn(_("Down"), self.on_go_down, False)
        ui['button_last'] = _btn(_("Last"), self.on_goto_last, False)
        ui['button_new'] = _btn(_("New"), self.on_new)
        ui['button_edit'] = _btn(_("Edit"), self.on_edit, False)
        ui['button_delete'] = _btn(_("Delete"), self.on_delete, False)

        main_hbox.append(button_box)

        content = dbox.get_content_area()
        content.set_spacing(4)
        content.append(main_hbox)

        self.dbox = dbox
        res = self._run_dialog(dbox)
        dbox.destroy()

        if res == Gtk.ResponseType.ACCEPT:
            self.update_cmd_list(store)
            self._save_config()
        self.dbox = None

    def update_cmd_list(self, store):
        it = store.get_iter_first()
        self.cmd_list = {}
        i = 0
        while it:
            (enabled, regexp, command) = store.get(it, CC_COL_ENABLED, CC_COL_REGEXP, CC_COL_COMMAND)
            self.cmd_list[i] = {'enabled': enabled, 'regexp': regexp, 'command': command}
            it = store.iter_next(it)
            i += 1

    def on_toggled(self, widget, path, data):
        treeview = data['treeview']
        store = treeview.get_model()
        it = store.get_iter(path)
        (enabled, regexp, command) = store.get(it, CC_COL_ENABLED, CC_COL_REGEXP, CC_COL_COMMAND)
        store.set_value(it, CC_COL_ENABLED, not enabled)

    def on_selection_changed(self, selection, data=None):
        (model, it) = selection.get_selected()
        has_sel = it is not None
        for key in ('button_top', 'button_up', 'button_down', 'button_last',
                    'button_edit', 'button_delete'):
            data[key].set_sensitive(has_sel)

    def _create_command_dialog(self, enabled_var=False, regexp_var="", command_var=""):
        dialog = Gtk.Dialog(title=_("New Command"), modal=True)
        dialog.add_button(_("_Cancel"), Gtk.ResponseType.REJECT)
        dialog.add_button(_("_OK"), Gtk.ResponseType.ACCEPT)

        if self.dbox:
            dialog.set_transient_for(self.dbox)

        grid = Gtk.Grid()
        grid.set_row_spacing(5)
        grid.set_column_spacing(5)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)

        label = Gtk.Label(label=_("Enabled:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, 0, 1, 1)
        enabled = Gtk.CheckButton()
        enabled.set_active(enabled_var)
        grid.attach(enabled, 1, 0, 1, 1)

        label = Gtk.Label(label=_("regexp:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, 1, 1, 1)
        regexp = Gtk.Entry()
        regexp.set_text(regexp_var)
        regexp.set_hexpand(True)
        grid.attach(regexp, 1, 1, 1, 1)

        label = Gtk.Label(label=_("Command:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, 2, 1, 1)
        command = Gtk.Entry()
        command.set_text(command_var)
        command.set_hexpand(True)
        grid.attach(command, 1, 2, 1, 1)

        content = dialog.get_content_area()
        content.append(grid)
        return (dialog, enabled, regexp, command)

    def on_new(self, button, data):
        (dialog, enabled, regexp, command) = self._create_command_dialog()
        res = self._run_dialog(dialog)
        item = {}
        if res == Gtk.ResponseType.ACCEPT:
            item['enabled'] = enabled.get_active()
            item['regexp'] = regexp.get_text()
            item['command'] = command.get_text()
            if item['regexp'] == '' or item['command'] == '':
                dialog.destroy()
                self._show_error(self.dbox, _("You need to define a regexp and command"))
                return
            store = data['treeview'].get_model()
            it = store.get_iter_first()
            regexp_exist = False
            while it is not None:
                if store.get_value(it, CC_COL_REGEXP) == item['regexp']:
                    regexp_exist = True
                    break
                it = store.iter_next(it)
            if not regexp_exist:
                store.append((item['enabled'], item['regexp'], item['command']))
            else:
                gerr(_("regexp *%s* already exist") % item['regexp'])
        dialog.destroy()

    def on_goto_top(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, it) = selection.get_selected()
        if not it:
            return
        firstiter = store.get_iter_first()
        store.move_before(it, firstiter)

    def on_go_up(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, it) = selection.get_selected()
        if not it:
            return
        tmpiter = store.get_iter_first()
        if store.get_path(tmpiter) == store.get_path(it):
            return
        while tmpiter:
            nxt = store.iter_next(tmpiter)
            if store.get_path(nxt) == store.get_path(it):
                store.swap(it, tmpiter)
                break
            tmpiter = nxt

    def on_go_down(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, it) = selection.get_selected()
        if not it:
            return
        nxt = store.iter_next(it)
        if nxt:
            store.swap(it, nxt)

    def on_goto_last(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, it) = selection.get_selected()
        if not it:
            return
        lastiter = it
        tmpiter = store.get_iter_first()
        while tmpiter:
            lastiter = tmpiter
            tmpiter = store.iter_next(tmpiter)
        store.move_after(it, lastiter)

    def on_delete(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, it) = selection.get_selected()
        if it:
            store.remove(it)

    def on_edit(self, button, data):
        treeview = data['treeview']
        selection = treeview.get_selection()
        (store, it) = selection.get_selected()
        if not it:
            return

        (dialog, enabled, regexp, command) = self._create_command_dialog(
            enabled_var=store.get_value(it, CC_COL_ENABLED),
            regexp_var=store.get_value(it, CC_COL_REGEXP),
            command_var=store.get_value(it, CC_COL_COMMAND))

        res = self._run_dialog(dialog)
        item = {}
        if res == Gtk.ResponseType.ACCEPT:
            item['enabled'] = enabled.get_active()
            item['regexp'] = regexp.get_text()
            item['command'] = command.get_text()
            if item['regexp'] == '' or item['command'] == '':
                dialog.destroy()
                self._show_error(self.dbox, _("You need to define a regexp and a command"))
                return
            tmpiter = store.get_iter_first()
            regexp_exist = False
            while tmpiter is not None:
                if (store.get_path(tmpiter) != store.get_path(it) and
                        store.get_value(tmpiter, CC_COL_REGEXP) == item['regexp']):
                    regexp_exist = True
                    break
                tmpiter = store.iter_next(tmpiter)
            if not regexp_exist:
                store.set(it,
                          CC_COL_ENABLED, item['enabled'],
                          CC_COL_REGEXP, item['regexp'],
                          CC_COL_COMMAND, item['command'])
            else:
                gerr(_("regexp *%s* already exist") % item['regexp'])
        dialog.destroy()
