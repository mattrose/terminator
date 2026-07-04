# Terminator by Chris Jones <cmsj@tenshu.net>
# GPL v2 only
"""terminal_popup_menu.py - classes necessary to provide a terminal context
menu"""

from gi.repository import GLib, Gtk, Gdk, Gio

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
        self.terminal = terminal
        self.terminator = Terminator()
        self.config = Config()

    def show(self, parent_widget, x=0, y=0):
        """Build and show a Gtk.PopoverMenu from Gio.Menu.

        On macOS with GTK 4.14+, PopoverMenu from Gio.Menu is routed through
        native NSMenu rather than a GdkPopup/NSPanel, so it is immune to the
        macOS auto-dismiss problem and can extend outside the window boundary.
        """
        terminal = self.terminal
        self.config.set_profile(terminal.get_profile())

        # URL detection
        url = None
        char_width = terminal.vte.get_char_width()
        char_height = terminal.vte.get_char_height()
        if char_width > 0 and char_height > 0:
            url = terminal.vte.match_check(int(x / char_width), int(y / char_height))

        menu = Gio.Menu()
        ag = Gio.SimpleActionGroup()
        _ctr = [0]

        def action(name, callback, enabled=True):
            a = Gio.SimpleAction(name=name)
            a.connect('activate', lambda _a, _p: callback())
            a.set_enabled(enabled)
            ag.add_action(a)

        def unique(prefix):
            _ctr[0] += 1
            return f'{prefix}-{_ctr[0]}'

        # ── URL section ────────────────────────────────────────────────────
        if url and url[0]:
            nameopen = _('Open link')
            namecopy = _('Copy address')
            if url[1] == terminal.matches.get('email'):
                nameopen = _('Send email to...')
                namecopy = _('Copy email address')
            elif url[1] == terminal.matches.get('voip'):
                nameopen = _('Call VoIP address')
                namecopy = _('Copy VoIP address')
            else:
                registry = plugin.PluginRegistry()
                registry.load_plugins()
                for urlplugin in registry.get_plugins_by_capability('url_handler'):
                    if terminal.matches.get(urlplugin.handler_name) == url[1]:
                        nameopen = _(urlplugin.nameopen)
                        namecopy = _(urlplugin.namecopy)
                        break
            sec = Gio.Menu()
            action('open-url', lambda: terminal.open_url(url, True))
            sec.append(nameopen, 'menu.open-url')
            action('copy-url', lambda: terminal.clipboard.set(terminal.prepare_url(url)))
            sec.append(namecopy, 'menu.copy-url')
            menu.append_section(None, sec)

        # ── Edit section ───────────────────────────────────────────────────
        sec = Gio.Menu()
        action('copy', lambda: terminal.vte.copy_clipboard(),
               enabled=terminal.vte.get_has_selection())
        sec.append(_('Copy'), 'menu.copy')
        action('paste', lambda: terminal.paste_clipboard())
        sec.append(_('Paste'), 'menu.paste')
        action('set-title', lambda: terminal.key_edit_window_title())
        sec.append(_('Set Window Title'), 'menu.set-title')
        menu.append_section(None, sec)

        # ── Split / tab section (not shown when zoomed) ────────────────────
        if not terminal.is_zoomed():
            sec = Gio.Menu()
            action('split-auto', lambda: terminal.emit('split-auto', terminal.get_cwd()))
            sec.append(_('Split Auto'), 'menu.split-auto')
            action('split-horiz', lambda: terminal.emit('split-horiz', terminal.get_cwd()))
            sec.append(_('Split Horizontally'), 'menu.split-horiz')
            action('split-vert', lambda: terminal.emit('split-vert', terminal.get_cwd()))
            sec.append(_('Split Vertically'), 'menu.split-vert')
            action('open-tab', lambda: terminal.emit('tab-new', False, terminal))
            sec.append(_('Open Tab'), 'menu.open-tab')
            if self.terminator.debug_address is not None:
                action('open-debug-tab', lambda: terminal.emit('tab-new', True, terminal))
                sec.append(_('Open Debug Tab'), 'menu.open-debug-tab')
            menu.append_section(None, sec)

        # ── Close ──────────────────────────────────────────────────────────
        sec = Gio.Menu()
        action('close', lambda: terminal.close())
        sec.append(_('Close'), 'menu.close')
        menu.append_section(None, sec)

        # ── Zoom ───────────────────────────────────────────────────────────
        sec = Gio.Menu()
        if not terminal.is_zoomed():
            sensitive = terminal.get_root() != terminal.get_parent()
            action('zoom', lambda: terminal.zoom(), enabled=sensitive)
            sec.append(_('Zoom terminal'), 'menu.zoom')
            action('maximise', lambda: terminal.maximise(), enabled=sensitive)
            sec.append(_('Maximise terminal'), 'menu.maximise')
        else:
            action('unzoom', lambda: terminal.unzoom())
            sec.append(_('Restore all terminals'), 'menu.unzoom')
        menu.append_section(None, sec)

        # ── Relaunch (only when process is held open) ──────────────────────
        if terminal.is_held_open:
            sec = Gio.Menu()
            action('relaunch', lambda: terminal.spawn_child())
            sec.append(_('Relaunch Command'), 'menu.relaunch')
            menu.append_section(None, sec)

        # ── Options ────────────────────────────────────────────────────────
        sec = Gio.Menu()
        action('readonly', lambda: terminal.do_readonly_toggle())
        sec.append(_('Read only'), 'menu.readonly')
        action('scrollbar', lambda: terminal.do_scrollbar_toggle())
        sec.append(_('Show scrollbar'), 'menu.scrollbar')
        def _open_prefs():
            PrefsEditor(terminal)
            return GLib.SOURCE_REMOVE
        action('preferences', lambda: GLib.idle_add(_open_prefs))
        sec.append(_('Preferences'), 'menu.preferences')
        menu.append_section(None, sec)

        # ── Colors submenu ─────────────────────────────────────────────────
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
        for theme_label, bg, fg in theme_items:
            aname = unique('color')
            b, f = bg, fg
            action(aname, lambda b=b, f=f: (terminal.set_bgcolor(b), terminal.set_fgcolor(f)))
            colors_menu.append(theme_label, f'menu.{aname}')
        action('pick-colors', lambda: self.pick_custom_colors(terminal))
        colors_menu.append(_('Custom...'), 'menu.pick-colors')
        sec = Gio.Menu()
        sec.append_submenu(_('Colors'), colors_menu)
        menu.append_section(None, sec)

        # ── Profiles submenu ───────────────────────────────────────────────
        profilelist = sorted(self.config.list_profiles(), key=str.lower)
        if len(profilelist) > 1:
            profiles_menu = Gio.Menu()
            for profile in profilelist:
                lbl = profile.capitalize() if profile == 'default' else profile
                aname = unique('profile')
                p = profile
                action(aname, lambda p=p: terminal.force_set_profile(None, p))
                profiles_menu.append(lbl, f'menu.{aname}')
            sec = Gio.Menu()
            sec.append_submenu(_('Profiles'), profiles_menu)
            menu.append_section(None, sec)

        # ── Layouts submenu ────────────────────────────────────────────────
        layouts = self.config.list_layouts()
        if layouts:
            layouts_menu = Gio.Menu()
            for layout in layouts:
                aname = unique('layout')
                l = layout
                action(aname, lambda l=l: spawn_new_terminator(
                    self.terminator.origcwd, ['-u', '-l', l]))
                layouts_menu.append(layout, f'menu.{aname}')
            sec = Gio.Menu()
            sec.append_submenu(_('Layouts...'), layouts_menu)
            menu.append_section(None, sec)

        # ── Plugin items ───────────────────────────────────────────────────
        try:
            menuitems = []
            registry = plugin.PluginRegistry()
            registry.load_plugins()
            for menuplugin in registry.get_plugins_by_capability('terminal_menu'):
                menuplugin.callback(menuitems, None, terminal)
            if menuitems:
                sec = Gio.Menu()
                self._add_plugin_items_to_menu(sec, menuitems, action, unique)
                menu.append_section(None, sec)
        except Exception as ex:
            err('TerminalPopupMenu::show: %s' % ex)

        # ── Build and show ─────────────────────────────────────────────────
        # Use sliding (not nested) so submenus open as separate panels instead
        # of expanding inline, which would make the menu taller than the screen.
        popover = Gtk.PopoverMenu.new_from_model_full(menu, Gtk.PopoverMenuFlags(0))
        popover.set_parent(parent_widget)
        popover.set_has_arrow(False)
        popover.insert_action_group('menu', ag)

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)

        popover.popup()
        return popover

    def _add_plugin_items_to_menu(self, gmenu, items, action_fn, unique_fn):
        """Recursively convert plugin menu items into Gio.Menu entries."""
        for item in items:
            if item is None:
                continue
            if not isinstance(item, tuple) or len(item) < 2:
                continue
            first, second = item[0], item[1]
            if first == 'check':
                label, is_active, cb = item[1], item[2], item[3]
                aname = unique_fn('plugin')
                prefix = '✓ ' if is_active else '   '
                action_fn(aname, lambda f=cb, a=is_active: f(None, not a))
                gmenu.append(prefix + label, f'menu.{aname}')
            elif isinstance(second, list):
                sub = Gio.Menu()
                self._add_plugin_items_to_menu(sub, second, action_fn, unique_fn)
                gmenu.append_submenu(first, sub)
            else:
                extra = item[2:] if len(item) > 2 else ()
                aname = unique_fn('plugin')
                action_fn(aname, lambda f=second, fa=extra: f(None, *fa))
                gmenu.append(first, f'menu.{aname}')

    def pick_custom_colors(self, terminal):
        """Open a dialog to choose background and foreground colors."""
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
            bg_hex = '#{:02x}{:02x}{:02x}'.format(
                int(bg_rgba.red * 255), int(bg_rgba.green * 255), int(bg_rgba.blue * 255))
            fg_hex = '#{:02x}{:02x}{:02x}'.format(
                int(fg_rgba.red * 255), int(fg_rgba.green * 255), int(fg_rgba.blue * 255))
            terminal.set_bgcolor(bg_hex, alpha=bg_rgba.alpha)
            terminal.set_fgcolor(fg_hex)
