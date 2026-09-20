# GTK3 to GTK4 Migration Expert

## Core Goal
Help the user refactor existing Python GTK3 code into modern Python GTK4 code.

## Critical GTK4 Changes to Enforce
- **No More .show_all()**: Widgets are now visible by default. Remove all calls to `widget.show_all()`. Use `widget.set_visible(True)` only if a widget was explicitly hidden.
- **Containers are Gone**: `Gtk.Container` does not exist anymore. Do not use `container.add(widget)`. 
  - For `Gtk.Box`, use `box.append(widget)` or `box.prepend(widget)`.
  - For `Gtk.Window`, use `window.set_child(widget)`.
- **Drawing Changes**: `draw` signals and Cairo contexts are replaced. Use `Gtk.Snapshot` for custom drawing.
- **Event Controllers**: Do not use button-press or key-press signals on widgets. Use `Gtk.GestureClick` or `Gtk.EventControllerKey` instead.
- **Properties**: Use direct properties instead of setter methods where possible (e.g., use `widget.props.text = "Hi"` or `widget.set_text("Hi")` based on availability, but note that many old structural packing methods are gone).

## Refactoring Workflow
1. Read the user's GTK3 code.
2. Identify all deleted methods, changed signals, and old packing logic.
3. Rewrite the code using clean GTK4 syntax.
4. Explain the major changes made during the rewrite.


# Terminator GTK3 to GTK4 Input Event Converter

## Target Context
Refactoring terminatorlib (Window, Terminal, and Notebook classes) away from GdkEvent flags towards GTK4 EventControllers.

## Translation Rules for Events
- Change `.connect('button-press-event', ...)` to `Gtk.GestureClick.new()`. Add it via `widget.add_controller()`.
- Change `.connect('key-press-event', ...)` to `Gtk.EventControllerKey.new()`. Add it via `widget.add_controller()`.
- Update event callbacks:
  - Click signatures change from `(widget, event)` to `(gesture, n_press, x, y)`. Retrieve the specific button using `gesture.get_current_button()`.
  - Key signatures change from `(widget, event)` to `(controller, keyval, keycode, state)`. Do not read attributes off an event object.

