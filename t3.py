import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk,Adw,Vte,Gio


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.box1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.box1)
        self.vte = Vte.Terminal()
        self.pid = self.vte.spawn_async(
                Vte.PtyFlags.DEFAULT,
                None, 
                ["/bin/bash"],
                None,
                0,
                None,
                None,
                -1,
                None,
                None,
                None,
            )
        self.box1.append(self.vte)
        evmrb = Gtk.GestureClick.new()
        evmrb.set_button(Gdk.BUTTON_SECONDARY)
        evmrb.connect("pressed", self.on_secondaryclick)  # could be "released"
        self.vte.add_controller(evmrb)
	# Things will go here
    def on_secondaryclick(self,*args):
        print(*args)
        menu = Gio.Menu.new()
        menu.append("Do Something", "win.something")
        self.popover = Gtk.PopoverMenu()
        self.popover.set_menu_model(menu)
        self.popover.set_parent(self.vte)
        action = Gio.SimpleAction.new("something", None)
        action.connect("activate", lambda x: print("something"))

class Terminal(Gtk.Box):
    def __init__(self):
        Gtk.__init__(self)


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()

app = MyApp(application_id="com.example.GtkApplication")
app.run(sys.argv)
