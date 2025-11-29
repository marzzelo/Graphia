import Graph

_ = Graph.GetText

PluginName = _("Show Console")
PluginVersion = "0.2"
PluginDescription = _("This is a very simple plugin that creates a menu item to show/hide the Python interpreter window.")

def Execute(Action):
    Graph.Form22.Visible = not Graph.Form22.Visible
    Action.Checked = Graph.Form22.Visible

Action = Graph.CreateAction(Caption=_("Show Python interpreter"), OnExecute=Execute, ShortCut="F11", IconFile="ShowConsole.png", Hint = _("Show the Python interpreter window."))
Graph.AddActionToMainMenu(Action)
