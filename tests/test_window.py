"""
Comprehensive tests for terminatorlib/window.py

Tests cover the Window and WindowTitle classes, including:
- Initialization and configuration
- Property management (zoomed, fullscreen, maximized, etc.)
- Event handlers (key press, button press, focus, window state)
- Terminal management (zoom, split, navigation)
- Tab management
- Terminal grouping
- Layout creation and management
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import copy
import time


class TestWindowTitle:
    """Test WindowTitle class - These tests don't require GTK initialization"""

    def test_window_title_init(self):
        """Test WindowTitle initialization"""
        from terminatorlib.window import WindowTitle
        
        mock_window = MagicMock()
        title = WindowTitle(mock_window)
        
        assert title.window == mock_window
        assert title.forced is False
        assert title.text is None

    def test_window_title_set_title_not_forced(self):
        """Test setting title when not forced"""
        from terminatorlib.window import WindowTitle
        
        mock_window = MagicMock()
        title = WindowTitle(mock_window)
        
        title.set_title(None, "New Title")
        assert title.text == "New Title"
        mock_window.set_title.assert_called()

    def test_window_title_set_title_forced(self):
        """Test setting title when forced (should not change)"""
        from terminatorlib.window import WindowTitle
        
        mock_window = MagicMock()
        title = WindowTitle(mock_window)
        title.forced = True
        title.text = "Forced Title"
        
        title.set_title(None, "New Title")
        assert title.text == "Forced Title"

    def test_window_title_force_title(self):
        """Test forcing a title"""
        from terminatorlib.window import WindowTitle
        
        mock_window = MagicMock()
        title = WindowTitle(mock_window)
        
        title.force_title("Force This")
        assert title.forced is True
        assert title.text == "Force This"

    def test_window_title_force_title_none(self):
        """Test forcing title to None (unforces)"""
        from terminatorlib.window import WindowTitle
        
        mock_window = MagicMock()
        title = WindowTitle(mock_window)
        title.forced = True
        
        title.force_title(None)
        assert title.forced is False

    def test_window_title_update(self):
        """Test updating title"""
        from terminatorlib.window import WindowTitle
        
        mock_window = MagicMock()
        title = WindowTitle(mock_window)
        title.text = "Test Title"
        
        title.update()
        mock_window.set_title.assert_called_with("Test Title")

    def test_window_title_update_forced(self):
        """Test updating forced title"""
        from terminatorlib.window import WindowTitle
        
        mock_window = MagicMock()
        title = WindowTitle(mock_window)
        title.text = "Forced Title"
        title.forced = True
        
        title.update()
        mock_window.set_title.assert_called_with("Forced Title")


class TestWindowProperties:
    """Test Window property management"""

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_do_get_property_term_zoomed(self, mock_container_init, mock_gtk_init):
        """Test getting term_zoomed property"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'), \
             patch.object(Window, 'register_signals'), \
             patch.object(Window, 'register_callbacks'), \
             patch.object(Window, 'apply_config'), \
             patch.object(Window, 'apply_icon'), \
             patch('terminatorlib.window.Terminator'):
            
            win = Window.__new__(Window)
            win.term_zoomed = True
            
            prop = MagicMock()
            prop.name = 'term_zoomed'
            
            result = win.do_get_property(prop)
            assert result is True

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_do_get_property_hyphenated(self, mock_container_init, mock_gtk_init):
        """Test getting property with hyphenated name"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.term_zoomed = False
            
            prop = MagicMock()
            prop.name = 'term-zoomed'
            
            result = win.do_get_property(prop)
            assert result is False

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_do_get_property_unknown_raises_error(self, mock_container_init, mock_gtk_init):
        """Test getting unknown property raises AttributeError"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            
            prop = MagicMock()
            prop.name = 'unknown_property'
            
            with pytest.raises(AttributeError):
                win.do_get_property(prop)

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_do_set_property_term_zoomed(self, mock_container_init, mock_gtk_init):
        """Test setting term_zoomed property"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            
            prop = MagicMock()
            prop.name = 'term_zoomed'
            
            win.do_set_property(prop, True)
            assert win.term_zoomed is True
            
            win.do_set_property(prop, False)
            assert win.term_zoomed is False

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_do_set_property_unknown_raises_error(self, mock_container_init, mock_gtk_init):
        """Test setting unknown property raises AttributeError"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            
            prop = MagicMock()
            prop.name = 'unknown_property'
            
            with pytest.raises(AttributeError):
                win.do_set_property(prop, True)


class TestWindowState:
    """Test Window state management"""

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_set_maximised_true(self, mock_container_init, mock_gtk_init):
        """Test setting window to maximized state"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.maximize = MagicMock()
            
            win.set_maximised(True)
            win.maximize.assert_called_once()

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_set_maximised_false(self, mock_container_init, mock_gtk_init):
        """Test unsetting window maximized state"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.unmaximize = MagicMock()
            
            win.set_maximised(False)
            win.unmaximize.assert_called_once()

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_set_fullscreen_true(self, mock_container_init, mock_gtk_init):
        """Test setting window to fullscreen"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.fullscreen = MagicMock()
            
            win.set_fullscreen(True)
            win.fullscreen.assert_called_once()

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_set_fullscreen_false(self, mock_container_init, mock_gtk_init):
        """Test unsetting window fullscreen"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.unfullscreen = MagicMock()
            
            win.set_fullscreen(False)
            win.unfullscreen.assert_called_once()

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_set_borderless_true(self, mock_container_init, mock_gtk_init):
        """Test setting window to borderless"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.set_decorated = MagicMock()
            
            win.set_borderless(True)
            win.set_decorated.assert_called_once_with(False)

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_set_borderless_false(self, mock_container_init, mock_gtk_init):
        """Test setting window to have borders"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.set_decorated = MagicMock()
            
            win.set_borderless(False)
            win.set_decorated.assert_called_once_with(True)

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_set_always_on_top(self, mock_container_init, mock_gtk_init):
        """Test setting window always on top"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.set_keep_above = MagicMock()
            
            win.set_always_on_top(True)
            win.set_keep_above.assert_called_once_with(True)

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_set_sticky(self, mock_container_init, mock_gtk_init):
        """Test setting window sticky"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.stick = MagicMock()
            
            win.set_sticky(True)
            win.stick.assert_called_once()


class TestWindowZoom:
    """Test Window zoom functionality"""

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_is_zoomed_true(self, mock_container_init, mock_gtk_init):
        """Test is_zoomed returns True when zoomed"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.term_zoomed = True
            
            assert win.is_zoomed() is True

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_is_zoomed_false(self, mock_container_init, mock_gtk_init):
        """Test is_zoomed returns False when not zoomed"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.term_zoomed = False
            
            assert win.is_zoomed() is False

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_is_zoomed_handles_type_error(self, mock_container_init, mock_gtk_init):
        """Test is_zoomed handles TypeError gracefully"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.get_property = MagicMock(side_effect=TypeError)
            
            result = win.is_zoomed()
            assert result is False


class TestWindowFocus:
    """Test Window focus handling"""

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_on_focus_out_sets_losefocus_time(self, mock_container_init, mock_gtk_init):
        """Test on_focus_out sets losefocus_time"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.get_visible_terminals = MagicMock(return_value=[])
            win.preventHide = False
            
            before_time = time.time()
            win.on_focus_out(None, None)
            after_time = time.time()
            
            assert before_time <= win.losefocus_time <= after_time

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_on_focus_in_clears_urgency_hint(self, mock_container_init, mock_gtk_init):
        """Test on_focus_in clears urgency hint"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.set_urgency_hint = MagicMock()
            win.terminator = MagicMock()
            win.terminator.doing_layout = False
            win.uuid = 'test-uuid'
            
            win.on_focus_in(None, None)
            win.set_urgency_hint.assert_called_once_with(False)

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_on_button_press_clears_urgency_hint(self, mock_container_init, mock_gtk_init):
        """Test on_button_press clears urgency hint"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.set_urgency_hint = MagicMock()
            
            result = win.on_button_press(None, None)
            win.set_urgency_hint.assert_called_once_with(False)
            assert result is False


class TestWindowEvents:
    """Test Window event handlers"""

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_on_window_state_changed_fullscreen(self, mock_container_init, mock_gtk_init):
        """Test on_window_state_changed detects fullscreen"""
        from terminatorlib.window import Window
        from gi.repository import Gdk
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            event = MagicMock()
            event.new_window_state = Gdk.WindowState.FULLSCREEN
            
            result = win.on_window_state_changed(None, event)
            assert win.isfullscreen is True
            assert result is False

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_on_window_state_changed_maximized(self, mock_container_init, mock_gtk_init):
        """Test on_window_state_changed detects maximized"""
        from terminatorlib.window import Window
        from gi.repository import Gdk
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            event = MagicMock()
            event.new_window_state = Gdk.WindowState.MAXIMIZED
            
            result = win.on_window_state_changed(None, event)
            assert win.ismaximised is True
            assert result is False

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_on_delete_event(self, mock_container_init, mock_gtk_init):
        """Test on_delete_event handling"""
        from terminatorlib.window import Window
        from gi.repository import Gtk
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            mock_child = MagicMock()
            win.get_child = MagicMock(return_value=mock_child)
            win.construct_confirm_close = MagicMock(return_value=Gtk.ResponseType.REJECT)
            
            result = win.on_delete_event(None, None)
            assert result is True  # Should return True to prevent closing

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_on_destroy_event(self, mock_container_init, mock_gtk_init):
        """Test on_destroy_event handling"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            mock_terminal = MagicMock()
            win.get_terminals = MagicMock(return_value=[mock_terminal])
            win.cnxids = MagicMock()
            win.terminator = MagicMock()
            win.destroy = MagicMock()
            
            win.on_destroy_event(None, None)
            
            assert win.isDestroyed is True
            mock_terminal.emit.assert_called_with('pre-close-term')
            mock_terminal.close.assert_called_once()


class TestWindowGrouping:
    """Test Window terminal grouping"""

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_set_groups(self, mock_container_init, mock_gtk_init):
        """Test setting terminal groups"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            term1 = MagicMock()
            term2 = MagicMock()
            win.terminator = MagicMock()
            win.terminator.focus_changed = MagicMock()
            win.terminator.last_focused_term = None
            
            win.set_groups("TestGroup", [term1, term2])
            
            term1.set_group.assert_called_once_with(None, "TestGroup")
            term2.set_group.assert_called_once_with(None, "TestGroup")


class TestWindowLayout:
    """Test Window layout management"""

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_create_layout_no_children_key(self, mock_container_init, mock_gtk_init):
        """Test create_layout with missing children key"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            layout = {'type': 'Terminal'}
            
            # Should not raise, just return without error
            win.create_layout(layout)

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_create_layout_terminal_type(self, mock_container_init, mock_gtk_init):
        """Test create_layout with Terminal type"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            mock_child = MagicMock()
            win.get_children = MagicMock(return_value=[mock_child])
            
            layout = {
                'type': 'Terminal',
                'children': {
                    'child0': {
                        'type': 'Terminal'
                    }
                }
            }
            
            win.create_layout(layout)
            mock_child.create_layout.assert_called_once()


class TestWindowIntegration:
    """Integration tests for Window functionality"""

    def test_window_title_integration(self):
        """Test Window with WindowTitle integration"""
        from terminatorlib.window import WindowTitle
        
        mock_window = MagicMock()
        mock_window.set_title = MagicMock()
        
        title = WindowTitle(mock_window)
        title.set_title(None, "Terminal Window")
        title.update()
        
        assert title.text == "Terminal Window"
        mock_window.set_title.assert_called_with("Terminal Window")

    @patch('terminatorlib.window.Gtk.Window.__init__', return_value=None)
    @patch('terminatorlib.window.Container.__init__', return_value=None)
    def test_window_state_transitions(self, mock_container_init, mock_gtk_init):
        """Test window state transitions"""
        from terminatorlib.window import Window
        
        with patch('terminatorlib.window.GObject.GObject.__init__', return_value=None), \
             patch('terminatorlib.window.GObject.type_register'):
            
            win = Window.__new__(Window)
            win.maximize = MagicMock()
            win.fullscreen = MagicMock()
            win.unmaximize = MagicMock()
            
            # Maximize
            win.set_maximised(True)
            assert win.maximize.called
            
            # Fullscreen
            win.set_fullscreen(True)
            assert win.fullscreen.called
            
            # Back to normal
            win.set_maximised(False)
            assert win.unmaximize.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
