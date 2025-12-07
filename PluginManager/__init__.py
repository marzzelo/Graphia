import Graph
import vcl
import os.path
import os
import Gui
import sys
import Utility

_ = Graph.GetText

PluginName = _("Plugin Manager")
PluginVersion = "1.0"
PluginDescription = _("The Plugin Manager allows you to mount and unmount Graph plugins. Unmounted plugins will not load on next Graph restart.")

# Directories to exclude from plugin tree
EXCLUDED_DIRS = {
    '__pycache__', '.git', '.vscode', '.venv', '.packages', 
    'common', 'docs', 'screenshots', '.agent'
}

# Files to exclude
EXCLUDED_FILES = {
    '__init__.py', '__init__.pyc', '.gitignore', '.env', '.env.example',
    'requirements.txt', 'install.bat', 'install.ps1', 'README.md',
    'PluginDoc.txt', 'Graph-Spanish.txt'
}


def get_plugins_dir():
    """Returns the Plugins directory path."""
    return os.path.dirname(os.path.dirname(__file__))


def is_plugin_mounted(plugin_path):
    """
    Check if a plugin is mounted (enabled).
    A plugin is mounted if its __init__.py exists (not renamed to .disabled).
    For single-file plugins, checks if the .py file exists (not .disabled).
    """
    if os.path.isdir(plugin_path):
        init_file = os.path.join(plugin_path, "__init__.py")
        init_pyc = os.path.join(plugin_path, "__init__.pyc")
        return os.path.exists(init_file) or os.path.exists(init_pyc)
    else:
        # Single file plugin
        return plugin_path.endswith('.py') and os.path.exists(plugin_path)


def is_plugin_disabled(plugin_path):
    """
    Check if a plugin has a disabled marker.
    """
    if os.path.isdir(plugin_path):
        disabled_file = os.path.join(plugin_path, "__init__.py.disabled")
        return os.path.exists(disabled_file)
    else:
        # Single file plugin
        disabled_path = plugin_path + ".disabled"
        return os.path.exists(disabled_path)


def mount_plugin(plugin_path):
    """
    Mount (enable) a plugin by renaming __init__.py.disabled back to __init__.py.
    """
    if os.path.isdir(plugin_path):
        disabled_file = os.path.join(plugin_path, "__init__.py.disabled")
        enabled_file = os.path.join(plugin_path, "__init__.py")
        if os.path.exists(disabled_file):
            os.rename(disabled_file, enabled_file)
            return True
    else:
        # Single file plugin
        disabled_path = plugin_path + ".disabled"
        if os.path.exists(disabled_path):
            # Remove the .disabled extension
            enabled_path = plugin_path
            os.rename(disabled_path, enabled_path)
            return True
    return False


def unmount_plugin(plugin_path):
    """
    Unmount (disable) a plugin by renaming __init__.py to __init__.py.disabled.
    """
    if os.path.isdir(plugin_path):
        enabled_file = os.path.join(plugin_path, "__init__.py")
        disabled_file = os.path.join(plugin_path, "__init__.py.disabled")
        if os.path.exists(enabled_file):
            os.rename(enabled_file, disabled_file)
            return True
    else:
        # Single file plugin
        if os.path.exists(plugin_path) and plugin_path.endswith('.py'):
            disabled_path = plugin_path + ".disabled"
            os.rename(plugin_path, disabled_path)
            return True
    return False


def is_plugin_dir(path):
    """Check if a directory is a valid plugin (has __init__.py or __init__.py.disabled)."""
    if not os.path.isdir(path):
        return False
    has_init = os.path.exists(os.path.join(path, "__init__.py"))
    has_init_pyc = os.path.exists(os.path.join(path, "__init__.pyc"))
    has_disabled = os.path.exists(os.path.join(path, "__init__.py.disabled"))
    return has_init or has_init_pyc or has_disabled


def is_single_file_plugin(filepath):
    """Check if a file is a single-file plugin (.py that's not __init__.py)."""
    basename = os.path.basename(filepath)
    if basename in EXCLUDED_FILES:
        return False
    # Exclude __init__.py.disabled (it's a disabled package marker, not a single-file plugin)
    if basename == '__init__.py.disabled':
        return False
    if basename.endswith('.py') and not basename.startswith('_'):
        return True
    if basename.endswith('.py.disabled') and not basename.startswith('_'):
        return True
    return False


def scan_plugins(base_dir, parent_path=""):
    """
    Recursively scan for plugins and return a tree structure.
    Returns list of dicts: {name, path, is_dir, mounted, children}
    """
    items = []
    
    try:
        entries = sorted(os.listdir(base_dir))
    except OSError:
        return items
    
    for entry in entries:
        full_path = os.path.join(base_dir, entry)
        rel_path = os.path.join(parent_path, entry) if parent_path else entry
        
        # Skip excluded directories
        if entry in EXCLUDED_DIRS:
            continue
        
        # Skip hidden files/folders
        if entry.startswith('.'):
            continue
        
        if os.path.isdir(full_path):
            if is_plugin_dir(full_path):
                # This is a plugin package
                mounted = is_plugin_mounted(full_path)
                children = scan_plugins(full_path, rel_path)
                items.append({
                    'name': entry,
                    'path': full_path,
                    'rel_path': rel_path,
                    'is_dir': True,
                    'mounted': mounted,
                    'children': children
                })
        else:
            # Check for single-file plugins
            if is_single_file_plugin(full_path):
                # Handle .disabled extension
                if entry.endswith('.py.disabled'):
                    display_name = entry[:-12]  # Remove .py.disabled
                    mounted = False
                    # Store the path without .disabled for consistency
                    actual_path = full_path[:-9]  # Remove .disabled
                else:
                    display_name = entry[:-3]  # Remove .py
                    mounted = True
                    actual_path = full_path
                
                items.append({
                    'name': display_name,
                    'path': actual_path,
                    'rel_path': rel_path.replace('.disabled', ''),
                    'is_dir': False,
                    'mounted': mounted,
                    'children': []
                })
    
    return items


class PluginManagerDialog:
    def __init__(self):
        self.plugins_dir = get_plugins_dir()
        self.node_data = {}  # Maps node to plugin data
        self.changes_made = False
        
        # Create form
        self.Form = vcl.TForm(None)
        self.Form.Caption = _("Plugin Manager")
        self.Form.Width = 500
        self.Form.Height = 450
        self.Form.Position = "poMainFormCenter"
        self.Form.BorderStyle = "bsSizeable"
        self.Form.Constraints.MinWidth = 400
        self.Form.Constraints.MinHeight = 350
        
        # Instructions label
        self.LblInfo = vcl.TLabel(self.Form)
        self.LblInfo.Parent = self.Form
        self.LblInfo.Left = 10
        self.LblInfo.Top = 10
        self.LblInfo.Width = 480
        self.LblInfo.AutoSize = False
        self.LblInfo.Height = 30
        self.LblInfo.WordWrap = True
        self.LblInfo.Caption = _("Select a plugin and click 'Toggle' to mount/unmount.")
        
        # TreeView for plugins
        self.TreeView = vcl.TTreeView(self.Form)
        self.TreeView.Parent = self.Form
        self.TreeView.Left = 10
        self.TreeView.Top = 45
        self.TreeView.Width = 465
        self.TreeView.Height = 290
        self.TreeView.Anchors = "akLeft,akTop,akRight,akBottom"
        self.TreeView.ReadOnly = True
        self.TreeView.HotTrack = True
        self.TreeView.OnDblClick = self.OnTreeDblClick
        self.TreeView.OnClick = self.OnTreeClick
        
        # Description panel
        self.PnlDesc = vcl.TPanel(self.Form)
        self.PnlDesc.Parent = self.Form
        self.PnlDesc.Left = 10
        self.PnlDesc.Top = 340
        self.PnlDesc.Width = 465
        self.PnlDesc.Height = 30
        self.PnlDesc.Anchors = "akLeft,akRight,akBottom"
        self.PnlDesc.BevelOuter = "bvNone"
        
        self.LblPath = vcl.TLabel(self.PnlDesc)
        self.LblPath.Parent = self.PnlDesc
        self.LblPath.Left = 0
        self.LblPath.Top = 5
        self.LblPath.Caption = ""
        self.LblPath.Font.Color = 0x666666
        
        # Buttons panel
        self.PnlButtons = vcl.TPanel(self.Form)
        self.PnlButtons.Parent = self.Form
        self.PnlButtons.Left = 0
        self.PnlButtons.Top = 375
        self.PnlButtons.Width = 500
        self.PnlButtons.Height = 45
        self.PnlButtons.Align = "alBottom"
        self.PnlButtons.BevelOuter = "bvNone"
        
        # Toggle button
        self.BtnToggle = vcl.TButton(self.PnlButtons)
        self.BtnToggle.Parent = self.PnlButtons
        self.BtnToggle.Caption = _("Toggle")
        self.BtnToggle.Width = 90
        self.BtnToggle.Height = 28
        self.BtnToggle.Left = 110
        self.BtnToggle.Top = 8
        self.BtnToggle.OnClick = self.OnToggle
        self.BtnToggle.Enabled = False
        
        # Import button
        self.BtnImport = vcl.TButton(self.PnlButtons)
        self.BtnImport.Parent = self.PnlButtons
        self.BtnImport.Caption = _("Import...")
        self.BtnImport.Width = 90
        self.BtnImport.Height = 28
        self.BtnImport.Left = 210
        self.BtnImport.Top = 8
        self.BtnImport.OnClick = self.OnImport
        
        # Close button
        self.BtnClose = vcl.TButton(self.PnlButtons)
        self.BtnClose.Parent = self.PnlButtons
        self.BtnClose.Caption = _("Close")
        self.BtnClose.Width = 90
        self.BtnClose.Height = 28
        self.BtnClose.Left = 390
        self.BtnClose.Top = 8
        self.BtnClose.Anchors = "akTop,akRight"
        self.BtnClose.Cancel = True
        self.BtnClose.ModalResult = 2
        
        # Load plugins tree
        self.Refresh()
    

    
    def Refresh(self):
        """Refresh the plugin tree."""
        self.TreeView.Items.Clear()
        self.node_data = {}
        
        plugins = scan_plugins(self.plugins_dir)
        self._add_nodes(None, plugins)
        
        # Expand all nodes
        for i in range(self.TreeView.Items.Count):
            self.TreeView.Items[i].Expand(True)
    
    def _add_nodes(self, parent, items):
        """Recursively add nodes to the tree."""
        for item in items:
            if parent is None:
                node = self.TreeView.Items.Add(None, self._get_display_text(item))
            else:
                node = self.TreeView.Items.AddChild(parent, self._get_display_text(item))
            
            # Store data for this node using AbsoluteIndex
            self.node_data[node.AbsoluteIndex] = item
            
            # Add children recursively
            if item['children']:
                self._add_nodes(node, item['children'])
    
    def _get_display_text(self, item):
        """Get display text for a plugin item with checkbox prefix."""
        name = item['name']
        # Use Unicode checkbox characters
        checkbox = "\u2611" if item['mounted'] else "\u2610"  # ☑ or ☐
        return f"{checkbox} {name}"
    
    def OnTreeDblClick(self, Sender):
        """Handle double click - toggle mount state."""
        node = self.TreeView.Selected
        if node:
            self._toggle_node(node)
    
    def OnTreeClick(self, Sender):
        """Handle tree click - update selection info."""
        node = self.TreeView.Selected
        if node:
            node_idx = node.AbsoluteIndex
            if node_idx in self.node_data:
                item = self.node_data[node_idx]
                self.LblPath.Caption = item['path']
                self.BtnToggle.Enabled = True
            else:
                self.BtnToggle.Enabled = False
        else:
            self.BtnToggle.Enabled = False
    
    def OnToggle(self, Sender):
        """Handle toggle button click."""
        node = self.TreeView.Selected
        if node:
            self._toggle_node(node)
    
    def _toggle_node(self, node):
        """Toggle the mount state of a plugin."""
        node_idx = node.AbsoluteIndex
        if node_idx not in self.node_data:
            return
        
        item = self.node_data[node_idx]
        
        # Don't allow unmounting PluginManager itself
        if item['name'] == 'PluginManager':
            vcl.Application.MessageBox(
                _("Cannot unmount the Plugin Manager itself."),
                _("Plugin Manager"),
                0x40  # MB_ICONINFORMATION
            )
            return
        
        if item['mounted']:
            # Unmount
            success = unmount_plugin(item['path'])
            if success:
                item['mounted'] = False
                self.changes_made = True
        else:
            # Mount
            success = mount_plugin(item['path'])
            if success:
                item['mounted'] = True
                self.changes_made = True
        
        # Update display
        node.Text = self._get_display_text(item)
        node.StateIndex = 1 if item['mounted'] else 2
    
    def OnImport(self, Sender):
        """Import a new plugin."""
        import shutil
        import zipfile
        
        Dialog = vcl.TOpenDialog(None)
        Dialog.Filter = "Graph plugin (*.py;*.pyc;*.zip)|*.py;*.pyc;*.zip"
        Dialog.Options = "ofHideReadOnly,ofEnableSizing,ofNoChangeDir,ofFileMustExist,ofDontAddToRecent"
        
        if not Dialog.Execute():
            return
        
        FileName = Dialog.FileName
        BaseName = os.path.basename(FileName)
        ModuleName, Ext = os.path.splitext(BaseName)
        
        PluginDir = os.environ.get('LOCALAPPDATA', '') + "\\Graph\\Plugins"
        DestPath = os.path.join(PluginDir, ModuleName) if Ext.lower() == ".zip" else os.path.join(PluginDir, BaseName)
        
        if os.path.exists(DestPath):
            if vcl.Application.MessageBox(
                _('Plugin "%s" is already installed. Do you want to overwrite it?') % ModuleName,
                _("Overwrite plugin?"), 0x24) != 6:
                return
        
        try:
            if Ext.lower() == ".zip":
                with zipfile.ZipFile(FileName) as File:
                    NameList = [Name.lower() for Name in File.namelist()]
                    if not "__init__.py" in NameList and not "__init__.pyc" in NameList:
                        vcl.Application.MessageBox(
                            _('"%s" is not a valid Graph plugin as it does not have a __init__.py file in the root.') % BaseName,
                            _('Install failed'), 0x10)
                        return
                    File.extractall(DestPath)
                Graph.LoadPlugin(PluginDir, ModuleName, True, True)
            else:
                os.makedirs(PluginDir, exist_ok=True)
                shutil.copy(FileName, PluginDir)
                Graph.LoadPlugin(PluginDir, BaseName, False, True)
            
            self.Refresh()
            
        except Exception as e:
            Graph.Form22.Visible = True
            raise
    
    def ShowModal(self):
        result = self.Form.ShowModal()
        
        if self.changes_made:
            vcl.Application.MessageBox(
                _("Plugin changes have been saved. Please restart Graph for changes to take effect."),
                _("Plugin Manager"),
                0x40  # MB_ICONINFORMATION
            )
        
        return result


def ShowPluginManager(Sender):
    global Dialog
    Dialog = PluginManagerDialog()
    Dialog.ShowModal()


Action = Graph.CreateAction(
    Caption=_("Plugin Manager"), 
    OnExecute=ShowPluginManager, 
    Hint=_("Mount and unmount Graph plugins."), 
    IconFile="PluginManager.png"
)
Graph.AddActionToMainMenu(Action)
