import terminatorlib.plugin as plugin

AVAILABLE = ['InsertTermName']

class InsertTermName(plugin.MenuItem):
   capabilities = ['terminal_menu']

   def __init__(self):
      plugin.MenuItem.__init__(self)

   def callback(self, menuitems, menu, terminal):
      menuitems.append(('Insert terminal name', lambda w: terminal.emit('insert-term-name')))
