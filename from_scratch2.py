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
        self.header = Gtk.HeaderBar()
        self.set_titlebar(self.header)

        # Create a new "Action"
        action = Gio.SimpleAction.new("something", None)
        action.connect("activate", self.term_container.split_horiz)
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

    def add_container(self):
        self.term_container.new()
        self.set_child(self.term_container)


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = Window(application=app)
        self.win.add_container()
        self.win.present()

class TerminalContainer(Gtk.Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.children = []
        self.terminal = None
    def new(self):
        self.terminal = Terminal()
        self.terminal.create_term()
        self.append(self.terminal)

    def split_horiz(self,action,params):
        print(self.terminal)
        # self.terminal.set_visible(False)
        self.remove(self.terminal)
        paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        paned.set_start_child(self.terminal)
        self.t2 = Terminal()
        self.t2.create_term()
        paned.set_end_child(self.t2)
        self.append(paned)
        # self.append(self.terminal_box.split())

class Terminal(Gtk.Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_hexpand(True)
        self.pid = None
        self.vte = None
    def create_term(self):
        # self.vte.set_size(80,25)
        self.vte = Vte.Terminal()
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
        print(self.pid)
        self.append(self.vte)
    def remove_term(self):
        self.remove(self.vte)
        if self.pid:
            print(self.pid)
        return self

app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)
