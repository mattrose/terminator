# Terminator by Chris Jones <cmsj@tenshu.net>
# GPL v2 only
"""terminal_popup_menu.py - classes necessary to provide a terminal context
menu"""

from gi.repository import Gtk, Gdk, Gio, GLib

from .version import APP_NAME
from .translation import _
from .terminator import Terminator
from .util import err, dbg, spawn_new_terminator
from .config import Config
from .prefseditor import PrefsEditor
from . import plugin

class TerminalPopupMenu(object):
    """Class implementing the Terminal context menu"""
    terminal = None
    terminator = None
    config = None

    def __init__(self, terminal):
        """Class initialiser"""
        self.terminal = terminal
        self.terminator = Terminator()
        self.config = Config()

    def show(self, widget, x=0, y=0):
        """Display the context menu"""
        terminal = self.terminal
        self.config.set_profile(terminal.get_profile())

        # Check for URL at click position using cell coordinates
        url = None
        char_width = terminal.vte.get_char_width()
        char_height = terminal.vte.get_char_height()
        if char_width > 0 and char_height > 0:
            url = terminal.vte.match_check(int(x / char_width), int(y / char_height))

        menu = Gio.Menu()
        actions = Gio.SimpleActionGroup()

        def add_action(name, callback, param_type=None):
            action = Gio.SimpleAction.new(name, param_type)
            action.connect('activate', callback)
            actions.add_action(action)
            return action

        # URL section
        if url and url[0]:
            dbg("URL matches id: %d" % url[1])
            nameopen = _('_Open link')
            namecopy = _('_Copy address')

            if url[1] == terminal.matches.get('email'):
                nameopen = _('_Send email to...')
                namecopy = _('_Copy email address')
            elif url[1] == terminal.matches.get('voip'):
                nameopen = _('Ca_ll VoIP address')
                namecopy = _('_Copy VoIP address')
            else:
                registry = plugin.PluginRegistry()
                registry.load_plugins()
                for urlplugin in registry.get_plugins_by_capability('url_handler'):
                    if terminal.matches.get(urlplugin.handler_name) == url[1]:
                        nameopen = _(urlplugin.nameopen)
                        namecopy = _(urlplugin.namecopy)
                        break

            add_action('open-url', lambda a, p: terminal.open_url(url, True))
            add_action('copy-url', lambda a, p: terminal.clipboard.set(terminal.prepare_url(url)))
            url_section = Gio.Menu()
            url_section.append(nameopen, 'popup.open-url')
            url_section.append(namecopy, 'popup.copy-url')
            menu.append_section(None, url_section)

        # Edit section
        copy_action = add_action('copy', lambda a, p: terminal.vte.copy_clipboard())
        copy_action.set_enabled(terminal.vte.get_has_selection())
        add_action('paste', lambda a, p: terminal.paste_clipboard())
        add_action('edit-window-title', lambda a, p: terminal.key_edit_window_title())
        edit_section = Gio.Menu()
        edit_section.append(_('_Copy'), 'popup.copy')
        edit_section.append(_('_Paste'), 'popup.paste')
        edit_section.append(_('Set _Window Title'), 'popup.edit-window-title')
        menu.append_section(None, edit_section)

        # Split/tab section (only if not zoomed)
        if not terminal.is_zoomed():
            split_section = Gio.Menu()
            add_action('split-auto', lambda a, p: terminal.emit('split-auto', terminal.get_cwd()))
            add_action('split-horiz', lambda a, p: terminal.emit('split-horiz', terminal.get_cwd()))
            add_action('split-vert', lambda a, p: terminal.emit('split-vert', terminal.get_cwd()))
            add_action('new-tab', lambda a, p: terminal.emit('tab-new', False, terminal))
            split_section.append(_('Split _Auto'), 'popup.split-auto')
            split_section.append(_('Split H_orizontally'), 'popup.split-horiz')
            split_section.append(_('Split V_ertically'), 'popup.split-vert')
            split_section.append(_('Open _Tab'), 'popup.new-tab')
            if self.terminator.debug_address is not None:
                add_action('debug-tab', lambda a, p: terminal.emit('tab-new', True, terminal))
                split_section.append(_('Open _Debug Tab'), 'popup.debug-tab')
            menu.append_section(None, split_section)

        # Close section
        close_section = Gio.Menu()
        add_action('close', lambda a, p: terminal.close())
        close_section.append(_('_Close'), 'popup.close')
        menu.append_section(None, close_section)

        # Zoom section
        zoom_section = Gio.Menu()
        if not terminal.is_zoomed():
            sensitive = terminal.get_root() != terminal.get_parent()
            zoom_action = add_action('zoom', lambda a, p: terminal.zoom())
            zoom_action.set_enabled(sensitive)
            max_action = add_action('maximise', lambda a, p: terminal.maximise())
            max_action.set_enabled(sensitive)
            zoom_section.append(_('_Zoom terminal'), 'popup.zoom')
            zoom_section.append(_('Ma_ximize terminal'), 'popup.maximise')
        else:
            add_action('unzoom', lambda a, p: terminal.unzoom())
            zoom_section.append(_('_Restore all terminals'), 'popup.unzoom')
        menu.append_section(None, zoom_section)

        # Grouping section (if titlebar hidden)
        if self.config['show_titlebar'] == False:
            group_menu = terminal.populate_group_menu()
            group_section = Gio.Menu()
            group_item = Gio.MenuItem.new_submenu(_('Grouping'), group_menu)
            group_section.append_item(group_item)
            menu.append_section(None, group_section)

        # Relaunch section (if held open)
        if terminal.is_held_open:
            add_action('relaunch', lambda a, p: terminal.spawn_child())
            relaunch_section = Gio.Menu()
            relaunch_section.append(_('Relaunch Command'), 'popup.relaunch')
            menu.append_section(None, relaunch_section)

        # Options section
        opts_section = Gio.Menu()
        add_action('toggle-readonly', lambda a, p: terminal.do_readonly_toggle())
        add_action('toggle-scrollbar', lambda a, p: terminal.do_scrollbar_toggle())
        add_action('preferences', lambda a, p: PrefsEditor(terminal))
        opts_section.append(_('_Read only'), 'popup.toggle-readonly')
        opts_section.append(_('Show _scrollbar'), 'popup.toggle-scrollbar')
        opts_section.append(_('_Preferences'), 'popup.preferences')
        menu.append_section(None, opts_section)

        # Colors submenu
        theme_items = [
            ('Solarized Light', '#eee8d5', '#586e75'),
            ('Solarized Dark', '#002b36', '#839496'),
            ('Monokai', '#272822', '#f8f8f2'),
            ('Dracula', '#282a36', '#f8f8f2'),
            ('Gruvbox Light', '#fbf1c7', '#3c3836'),
            ('Gruvbox Dark', '#282828', '#ebdbb2'),
            ('Nord', '#2e3440', '#d8dee9'),
            ('One Light', '#fafafa', '#383a42'),
            ('One Dark', '#1d1f21', '#c5c8c6'),
            ('Zenburn', '#3f3f3f', '#dcdccc'),
            ('Nightfox', '#1a1b26', '#c0caf5'),
            ('Taiwanese Blue', '#005695', '#ffffff'),
            ('Solarized Blue', '#073642', '#93a1a1'),
        ]
        colors_menu = Gio.Menu()
        for i, (theme_label, bg, fg) in enumerate(theme_items):
            aname = 'theme-%d' % i
            add_action(aname, lambda a, p, b=bg, f=fg: (terminal.set_bgcolor(b), terminal.set_fgcolor(f)))
            colors_menu.append(theme_label, 'popup.' + aname)
        colors_menu.append(_('_Custom...'), 'popup.custom-colors')
        add_action('custom-colors', lambda a, p: self.pick_custom_colors(terminal))
        colors_item = Gio.MenuItem.new_submenu(_('_Colors'), colors_menu)
        colors_section = Gio.Menu()
        colors_section.append_item(colors_item)
        menu.append_section(None, colors_section)

        # Profiles submenu (if more than one profile)
        profilelist = sorted(self.config.list_profiles(), key=str.lower)
        if len(profilelist) > 1:
            profiles_menu = Gio.Menu()
            current_profile = terminal.get_profile()
            for j, profile in enumerate(profilelist):
                profile_label = profile.capitalize() if profile == 'default' else profile
                aname = 'profile-%d' % j
                add_action(aname, lambda a, p, prof=profile: terminal.force_set_profile(None, prof))
                profiles_menu.append(profile_label, 'popup.' + aname)
            profiles_item = Gio.MenuItem.new_submenu(_('Profiles'), profiles_menu)
            profiles_section = Gio.Menu()
            profiles_section.append_item(profiles_item)
            menu.append_section(None, profiles_section)

        # Layouts submenu
        layouts = self.config.list_layouts()
        if layouts:
            layouts_menu = Gio.Menu()
            for k, layout in enumerate(layouts):
                aname = 'layout-%d' % k
                add_action(aname, lambda a, p, lay=layout: spawn_new_terminator(self.terminator.origcwd, ['-u', '-l', lay]))
                layouts_menu.append(layout, 'popup.' + aname)
            layouts_item = Gio.MenuItem.new_submenu(_('_Layouts...'), layouts_menu)
            layouts_section = Gio.Menu()
            layouts_section.append_item(layouts_item)
            menu.append_section(None, layouts_section)

        # Plugin menu items — plugins append (label, callback, *args) tuples,
        # or ('check', label, is_active, callback) for toggle items,
        # or (label, [(sublabel, callback, *args), ...]) for submenus.
        try:
            menuitems = []
            registry = plugin.PluginRegistry()
            registry.load_plugins()
            plugins = registry.get_plugins_by_capability('terminal_menu')
            for menuplugin in plugins:
                menuplugin.callback(menuitems, menu, terminal)
            if menuitems:
                plugin_section = Gio.Menu()
                plugin_counter = [0]

                def _process_plugin_items(items, section):
                    for item in items:
                        if item is None:
                            continue
                        if not isinstance(item, tuple) or len(item) < 2:
                            continue
                        first = item[0]
                        second = item[1]
                        if first == 'check':
                            # ('check', label, is_active, callback)
                            label, is_active, cb = item[1], item[2], item[3]
                            n = 'plugin-check-%d' % plugin_counter[0]
                            plugin_counter[0] += 1
                            state = GLib.Variant('b', bool(is_active))
                            action = Gio.SimpleAction.new_stateful(n, None, state)
                            def _on_check(a, v, f=cb):
                                a.set_state(v)
                                f(None, v.get_boolean())
                            action.connect('change-state', _on_check)
                            actions.add_action(action)
                            section.append(label, 'popup.' + n)
                        elif isinstance(second, list):
                            # (label, [(sublabel, callback, *args), ...])
                            sub_menu = Gio.Menu()
                            _process_plugin_items(second, sub_menu)
                            section.append_item(Gio.MenuItem.new_submenu(first, sub_menu))
                        elif first is None:
                            pass  # separator placeholder — ignored
                        else:
                            # (label, callback, *args)
                            extra = item[2:] if len(item) > 2 else ()
                            n = 'plugin-%d' % plugin_counter[0]
                            plugin_counter[0] += 1
                            action = Gio.SimpleAction.new(n, None)
                            def _on_act(a, p, f=second, fa=extra):
                                f(None, *fa)
                            action.connect('activate', _on_act)
                            actions.add_action(action)
                            section.append(first, 'popup.' + n)

                _process_plugin_items(menuitems, plugin_section)
                if plugin_section.get_n_items() > 0:
                    menu.append_section(None, plugin_section)
        except Exception as ex:
            err('TerminalPopupMenu::show: %s' % ex)

        # Create and show the popover.
        # Parent to the terminal Box (not terminal.vte) so that GTK4's action
        # group lookup isn't confused by VTE's own event handling.
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(terminal)

        # Translate click coordinates from VTE-space into terminal-Box-space.
        try:
            px, py = terminal.vte.translate_coordinates(terminal, x, y)
        except (TypeError, AttributeError):
            px, py = x, y

        rect = Gdk.Rectangle()
        rect.x = int(px)
        rect.y = int(py)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)
        popover.set_has_arrow(False)

        terminal.insert_action_group('popup', actions)

        def on_closed(p):
            p.unparent()
            terminal.insert_action_group('popup', None)
        popover.connect('closed', on_closed)
        popover.popup()
        return True

    def pick_custom_colors(self, terminal):
        """Open a dialog to choose background and foreground colors"""
        dialog = Gtk.Dialog(title=_('Pick Terminal Colors'),
                            transient_for=terminal.get_root(),
                            modal=True)
        dialog.add_button(_('Cancel'), Gtk.ResponseType.CANCEL)
        dialog.add_button(_('Apply'), Gtk.ResponseType.OK)

        content = dialog.get_content_area()
        content.set_spacing(8)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(8)
        grid.set_margin_top(12)
        grid.set_margin_bottom(12)
        grid.set_margin_start(12)
        grid.set_margin_end(12)

        bg_label = Gtk.Label(label=_('Background:'))
        bg_label.set_halign(Gtk.Align.START)
        bg_btn = Gtk.ColorButton()
        bg_btn.set_use_alpha(True)
        if terminal.bgcolor is not None:
            bg_btn.set_rgba(terminal.bgcolor.copy())

        fg_label = Gtk.Label(label=_('Text:'))
        fg_label.set_halign(Gtk.Align.START)
        fg_btn = Gtk.ColorButton()
        if terminal.fgcolor_active is not None:
            fg_initial = terminal.fgcolor_active.copy()
            fg_initial.alpha = 1.0
            fg_btn.set_rgba(fg_initial)

        grid.attach(bg_label, 0, 0, 1, 1)
        grid.attach(bg_btn, 1, 0, 1, 1)
        grid.attach(fg_label, 0, 1, 1, 1)
        grid.attach(fg_btn, 1, 1, 1, 1)
        content.append(grid)

        result = [Gtk.ResponseType.CANCEL]
        loop = GLib.MainLoop()
        def on_response(d, r):
            result[0] = r
            d.destroy()
            loop.quit()
        dialog.connect('response', on_response)
        dialog.present()
        loop.run()

        if result[0] == Gtk.ResponseType.OK:
            bg_rgba = bg_btn.get_rgba()
            fg_rgba = fg_btn.get_rgba()
            bg_hex = "#{0:02x}{1:02x}{2:02x}".format(
                int(bg_rgba.red * 255),
                int(bg_rgba.green * 255),
                int(bg_rgba.blue * 255))
            fg_hex = "#{0:02x}{1:02x}{2:02x}".format(
                int(fg_rgba.red * 255),
                int(fg_rgba.green * 255),
                int(fg_rgba.blue * 255))
            terminal.set_bgcolor(bg_hex, alpha=bg_rgba.alpha)
            terminal.set_fgcolor(fg_hex)
