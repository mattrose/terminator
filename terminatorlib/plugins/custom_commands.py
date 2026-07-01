# Terminator by Chris Jones <cmsj@tenshu.net>
# GPL v2 only
#
# -added keybinding, bookmark functionality
# -made name parsing to menu, optional
#   - Vishweshwar Saran Singh Deo vssdeo@gmail.com

"""custom_commands.py - Terminator Plugin to add custom command menu entries"""
import sys
import os
import time

if __name__ == '__main__':
  sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from gi.repository import Gtk, GObject, GLib, Gdk
import terminatorlib.plugin as plugin
from terminatorlib.config import Config
from terminatorlib.translation import _
from terminatorlib.util import get_config_dir, err, dbg, gerr
from terminatorlib.terminator import Terminator

from terminatorlib.plugin import KeyBindUtil

(CC_COL_ENABLED, CC_COL_NAME, CC_COL_NAME_PARSE, CC_COL_COMMAND) = list(range(0, 4))

PluginActAdd = "plugin_add"
PluginActBmk = "plugin_bmk"

PluginAddDesc = "Plugin Add Bookmark"
PluginBmkDesc = "Plugin Open Bookmark Preferences"

AVAILABLE = ['CustomCommandsMenu']

class CustomCommandsMenu(plugin.MenuItem):
    """Add custom commands to the terminal menu"""
    capabilities = ['terminal_menu']
    cmd_list = {}
    conf_file = os.path.join(get_config_dir(), "custom_commands")
    keyb = None

    def __init__(self):
        self.dbox = None
        self._key_controllers = []

        config = Config()
        sections = config.plugin_get_config(self.__class__.__name__)

        self.connect_signals()
        self.keyb = KeyBindUtil(config)
        self.keyb.bindkey_check_config([PluginAddDesc, PluginActAdd, "<Alt>b"])
        self.keyb.bindkey_check_config([PluginBmkDesc, PluginActBmk, "<Shift><Alt>b"])

        if not isinstance(sections, dict):
            return
        noord_cmds = []
        for part in sections:
            s = sections[part]
            if not ("name" in s and "command" in s):
                print("CustomCommandsMenu: Ignoring section %s" % s)
                continue
            name = s["name"]
            name_parse = s.get("name_parse", "True")
            command = s["command"]
            enabled = s["enabled"] and s["enabled"] or False
            if "position" in s:
                self.cmd_list[int(s["position"])] = {'enabled': enabled,
                                                     'name': name,
                                                     'name_parse': name_parse,
                                                     'command': command}
            else:
                noord_cmds.append({'enabled': enabled,
                                   'name': name,
                                   'name_parse': name_parse,
                                   'command': command})
            for cmd in noord_cmds:
                self.cmd_list[len(self.cmd_list)] = cmd

    def unload(self):
        dbg("unloading")
        for window, ctrl in self._key_controllers:
            try:
                window.remove_controller(ctrl)
            except Exception:
                dbg("no connected signals")
        self._key_controllers = []
        self.keyb.unbindkey([PluginAddDesc, PluginActAdd, "<Alt>b"])
        self.keyb.unbindkey([PluginBmkDesc, PluginActBmk, "<Shift><Alt>b"])

    def connect_signals(self):
        self.windows = Terminator().get_windows()
        for window in self.windows:
            ctrl = Gtk.EventControllerKey()
            ctrl.connect('key-pressed', self.on_keypress)
            window.add_controller(ctrl)
            self._key_controllers.append((window, ctrl))

    def get_last_exe_cmd(self):
        from terminatorlib.keybindings import KeyEventProxy
        cur_win = Terminator().last_focused_term.get_root()
        focus_term = cur_win.get_focussed_terminal()
        tmp_file = os.path.join(os.sep, 'tmp', 'term_cmd')
        command = 'fc -n -l -1 -1 > ' + tmp_file + '; #bookmark last cmd\n'
        focus_term.vte.feed_child(str(command).encode("utf-8"))

        fsz = 0
        count = 0
        while not (count == 2 or fsz):
            time.sleep(0.1)
            if os.path.exists(tmp_file):
                fsz = os.path.getsize(tmp_file)
                count += 1

        last_cmd = None
        try:
            with open(tmp_file, 'r') as file:
                last_cmd = file.read()
        except Exception as ex:
            err('Unable to open \'%s\' ex: (%s)' % (tmp_file, ex))

        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        if last_cmd:
            last_cmd = last_cmd.rstrip()
        dbg('last exec cmd: (%s)' % last_cmd)
        return last_cmd

    def get_last_exe_cmd_dialog_vars(self):
        last_exe_cmd = self.get_last_exe_cmd()
        return {'enabled': True,
                'name': last_exe_cmd,
                'name_parse': False,
                'command': last_exe_cmd}

    def on_keypress(self, ctrl, keyval, keycode, state):
        from terminatorlib.keybindings import KeyEventProxy
        event = KeyEventProxy(keyval, keycode, state)
        act = self.keyb.keyaction(event)
        dbg("keyaction: (%s) (%s)" % (str(act), keyval))

        if act == PluginActAdd:
            dbg("add bookmark")
            self.setup_store()
            dialog_vars = self.get_last_exe_cmd_dialog_vars()
            self.on_new(None, {'dialog_vars': dialog_vars})
            self.update_cmd_list(self.store)
            self._save_config()
            return True

        if act == PluginActBmk:
            dbg("open custom command preferences")
            self.configure(None)
            return True

    def callback(self, menuitems, menu, terminal):
        """Add our menu items to the menu"""
        subitems = [(_('Preferences'), self.configure)]
        submenus = {}

        for command in [self.cmd_list[key] for key in sorted(self.cmd_list.keys())]:
            if not command['enabled']:
                continue
            if not command['name_parse']:
                leaf_name = command['name']
                branch_names = []
            else:
                leaf_name = command['name'].split('/')[-1]
                branch_names = command['name'].split('/')[:-1]

            terminals = terminal.terminator.get_target_terms(terminal)

            target_list = subitems
            for idx in range(len(branch_names)):
                lookup_name = '/'.join(branch_names[0:idx + 1])
                if lookup_name not in submenus:
                    new_sub = []
                    submenus[lookup_name] = new_sub
                    parent_key = '/'.join(branch_names[0:idx]) if idx > 0 else ''
                    parent_list = submenus[parent_key] if parent_key else subitems
                    parent_list.append((branch_names[idx], new_sub))
                target_list = submenus[lookup_name]

            target_list.append((leaf_name, self._execute,
                                {'terminals': terminals, 'command': command['command']}))

        menuitems.append((_('Custom Commands'), subitems))

    def _save_config(self):
        config = Config()
        config.plugin_del_config(self.__class__.__name__)
        i = 0
        for command in [self.cmd_list[key] for key in sorted(self.cmd_list.keys())]:
            enabled = command['enabled']
            name = command['name']
            name_parse = command['name_parse']
            cmd = command['command']

            item = {'enabled': enabled, 'name': name, 'name_parse': name_parse,
                    'command': cmd, 'position': i}
            config.plugin_set(self.__class__.__name__, name, item)
            i += 1
        config.save()

    def _execute(self, widget, data):
        command = data['command']
        if command[-1] != '\n':
            command = command + '\n'
        for terminal in data['terminals']:
            terminal.vte.feed_child(command.encode())

    def setup_store(self):
        self.store = Gtk.ListStore(bool, str, bool, str)
        for command in [self.cmd_list[key] for key in sorted(self.cmd_list.keys())]:
            self.store.append([command['enabled'], command['name'],
                               command['name_parse'], command['command']])
        return self.store

    def configure(self, widget, data=None):
        ui = {}
        dbox = Gtk.Dialog(title=_("Custom Commands Configuration"), modal=True)
        dbox.add_button(_("_Cancel"), Gtk.ResponseType.REJECT)
        dbox.add_button(_("_OK"), Gtk.ResponseType.ACCEPT)

        if widget and hasattr(widget, 'get_root'):
            dbox.set_transient_for(widget.get_root())

        try:
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            if icon_theme.has_icon('terminator-custom-commands'):
                dbox.set_icon_name('terminator-custom-commands')
        except Exception:
            dbg('Unable to load Terminator custom command icon')

        store = self.setup_store()

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
        column = Gtk.TreeViewColumn(_("Name"), renderer, text=CC_COL_NAME)
        treeview.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Command"), renderer, text=CC_COL_COMMAND)
        treeview.append_column(column)

        scroll_window = Gtk.ScrolledWindow()
        scroll_window.set_size_request(500, 250)
        scroll_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_window.set_child(treeview)

        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        main_hbox.set_hexpand(True)
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
        ui['button_save_last_cmd'] = _btn(_("Bookmark Last Cmd"), self.on_last_exe_cmd)

        main_hbox.append(button_box)

        content = dbox.get_content_area()
        content.set_spacing(4)
        content.append(main_hbox)

        self.dbox = dbox
        result = [Gtk.ResponseType.REJECT]
        loop = GLib.MainLoop()

        def on_response(d, r):
            result[0] = r
            loop.quit()

        dbox.connect('response', on_response)
        dbox.present()
        loop.run()
        dbox.destroy()

        if result[0] == Gtk.ResponseType.ACCEPT:
            self.update_cmd_list(store)
            self._save_config()
        self.dbox = None

    def update_cmd_list(self, store):
        it = store.get_iter_first()
        self.cmd_list = {}
        i = 0
        while it:
            (enabled, name, name_parse, command) = store.get(it,
                                                             CC_COL_ENABLED,
                                                             CC_COL_NAME,
                                                             CC_COL_NAME_PARSE,
                                                             CC_COL_COMMAND)
            self.cmd_list[i] = {'enabled': enabled, 'name': name,
                                'name_parse': name_parse, 'command': command}
            it = store.iter_next(it)
            i += 1

    def on_toggled(self, widget, path, data):
        treeview = data['treeview']
        store = treeview.get_model()
        it = store.get_iter(path)
        (enabled, name, command) = store.get(it, CC_COL_ENABLED, CC_COL_NAME, CC_COL_COMMAND)
        store.set_value(it, CC_COL_ENABLED, not enabled)

    def on_selection_changed(self, selection, data=None):
        (model, it) = selection.get_selected()
        has_sel = it is not None
        for key in ('button_top', 'button_up', 'button_down', 'button_last',
                    'button_edit', 'button_delete'):
            data[key].set_sensitive(has_sel)

    def _create_command_dialog(self, enabled_var=False, name_var="",
                               name_parse_var="", command_var=""):
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

        label = Gtk.Label(label=_("Parse Name into SubMenu's:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, 1, 1, 1)
        name_parse = Gtk.CheckButton()
        name_parse.set_active(name_parse_var)
        grid.attach(name_parse, 1, 1, 1, 1)

        label = Gtk.Label(label=_("Name:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, 2, 1, 1)
        name = Gtk.Entry()
        name.set_text(name_var)
        name.set_hexpand(True)
        grid.attach(name, 1, 2, 1, 1)

        label = Gtk.Label(label=_("Command:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 0, 3, 1, 1)
        command = Gtk.TextView()
        command.set_hexpand(True)
        command.set_vexpand(True)
        command.get_buffer().set_text(command_var)
        grid.attach(command, 1, 3, 1, 1)

        content = dialog.get_content_area()
        content.append(grid)
        return (dialog, enabled, name, name_parse, command)

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

    def on_last_exe_cmd(self, button, data):
        new_data = data.copy()
        new_data['dialog_vars'] = self.get_last_exe_cmd_dialog_vars()
        self.on_new(button, new_data)

    def on_new(self, button, data):
        enabled_var = ''
        name_var = ''
        name_parse_var = ''
        command_var = ''

        if data and 'dialog_vars' in data:
            dialog_vars = data.get('dialog_vars', {})
            enabled_var = dialog_vars.get('enabled', True)
            name_var = dialog_vars.get('name', '')
            name_parse_var = dialog_vars.get('name_parse', False)
            command_var = dialog_vars.get('command', '')

        (dialog, enabled, name, name_parse, command) = self._create_command_dialog(
            enabled_var=enabled_var,
            name_var=name_var,
            name_parse_var=name_parse_var,
            command_var=command_var)

        res = self._run_dialog(dialog)
        item = {}
        if res == Gtk.ResponseType.ACCEPT:
            item['enabled'] = enabled.get_active()
            item['name'] = name.get_text()
            item['name_parse'] = name_parse.get_active()
            item['command'] = command.get_buffer().get_text(
                command.get_buffer().get_start_iter(),
                command.get_buffer().get_end_iter(), True)
            if item['name'] == '' or item['command'] == '':
                dialog.destroy()
                self._show_error(self.dbox, _("You need to define a name and command"))
                return
            store = data['treeview'].get_model() if data and 'treeview' in data else None
            if not store:
                store = self.setup_store()
            it = store.get_iter_first()
            name_exist = False
            while it is not None:
                if store.get_value(it, CC_COL_NAME) == item['name']:
                    name_exist = True
                    break
                it = store.iter_next(it)
            if not name_exist:
                store.append((item['enabled'], item['name'],
                              item['name_parse'], item['command']))
            else:
                gerr(_("Name *%s* already exist") % item['name'])
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

        (dialog, enabled, name, name_parse, command) = self._create_command_dialog(
            enabled_var=store.get_value(it, CC_COL_ENABLED),
            name_var=store.get_value(it, CC_COL_NAME),
            name_parse_var=store.get_value(it, CC_COL_NAME_PARSE),
            command_var=store.get_value(it, CC_COL_COMMAND))

        res = self._run_dialog(dialog)
        item = {}
        if res == Gtk.ResponseType.ACCEPT:
            item['enabled'] = enabled.get_active()
            item['name'] = name.get_text()
            item['name_parse'] = name_parse.get_active()
            item['command'] = command.get_buffer().get_text(
                command.get_buffer().get_start_iter(),
                command.get_buffer().get_end_iter(), True)
            if item['name'] == '' or item['command'] == '':
                dialog.destroy()
                self._show_error(self.dbox, _("You need to define a name and command"))
                return
            tmpiter = store.get_iter_first()
            name_exist = False
            while tmpiter is not None:
                if (store.get_path(tmpiter) != store.get_path(it) and
                        store.get_value(tmpiter, CC_COL_NAME) == item['name']):
                    name_exist = True
                    break
                tmpiter = store.iter_next(tmpiter)
            if not name_exist:
                store.set(it,
                          CC_COL_ENABLED, item['enabled'],
                          CC_COL_NAME, item['name'],
                          CC_COL_NAME_PARSE, item['name_parse'],
                          CC_COL_COMMAND, item['command'])
            else:
                gerr(_("Name *%s* already exist") % item['name'])
        dialog.destroy()


if __name__ == '__main__':
    c = CustomCommandsMenu()
    c.configure(None, None)
    GLib.MainLoop().run()
