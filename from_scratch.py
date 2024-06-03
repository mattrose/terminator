#!/usr/bin/python

### Next on the list.
# How to make the terminal box widen when the application window widens
import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Vte','3.91')
from gi.repository import Gtk, Adw, Vte, Gio


class Window(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Things will go here
        self.term_container = TerminalContainer()
        tb = TerminalBox()
        self.set_child(self.term_container)
        self.header = Gtk.HeaderBar()
        self.set_titlebar(self.header)

        # Create a new "Action"
        action = Gio.SimpleAction.new("something", None)
        action.connect("activate", tb.print_something)
        self.add_action(action)  # Here the action is being added to the window, but you could add it to the
                                 # application or an "ActionGroup"

        # Create a new menu, containing that action
        menu = Gio.Menu.new()
        menu.append("Do Something", "win.something")  # Or you would do app.something if you had attached the
                                                      # action to the application

        # Create a popover
        self.popover = Gtk.PopoverMenu()  # Create a new popover menu
        self.popover.set_menu_model(menu)

        # Create a menu button
        self.hamburger = Gtk.MenuButton()
        self.hamburger.set_popover(self.popover)
        self.hamburger.set_icon_name("open-menu-symbolic")  # Give it a nice icon

        # Add menu button to the header bar
        self.header.pack_start(self.hamburger)

class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = Window(application=app)
        self.win.present()

class TerminalContainer(Gtk.Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.terminal_box = TerminalBox()
        self.append(self.terminal_box)

class TerminalBox(Gtk.Paned):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.terminal = Terminal()
        # self.append(self.terminal)
        self.terminal2 = Terminal()
        self.set_start_child(self.terminal)
        # self.set_resize_start_child(True)
        self.set_shrink_start_child(True)
        self.set_end_child(self.terminal2)
        # self.set_resize_end_child(True)
        self.set_shrink_end_child(True)

    def print_something(self, action, param):
        print("Something!")
        print(self.terminal.get_size())
"""
        self.set_start_child(self.terminal)
        self.set_end_child(self.terminal2)
        self.set_resize_end_child(True)
        self.set_shrink_end_child(True)
        print("Something!")
"""   
class Terminal(Gtk.Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_hexpand(True)
        self.vte = Vte.Terminal()
        self.vte.set_hexpand(True)
        # self.vte.set_size(80,25)
        args = ["/bin/bash"]
        self.pid = self.vte.spawn_async(
                Vte.PtyFlags.DEFAULT,
                None,
                args,
                None,
                0,
                None,
                None,
                -1,
                None,
                None,
                None,
            )
        self.append(self.vte)

app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)
