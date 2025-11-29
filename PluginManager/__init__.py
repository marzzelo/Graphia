import Graph
import vcl
import os.path
import shutil
import zipfile
import Gui
import sys
import Utility

_ = Graph.GetText

PluginName = _("Plugin Manager")
PluginVersion = "0.3"
PluginDescription = _("The Plugin Manager is used to install and remove Graph plugins from  a single .py file or a package in a .zip file.")

def ShowImportDialog():
    Dialog = vcl.TOpenDialog(None)
    Dialog.Filter = "Graph plugin (*.py;*.pyc;*.zip)|*.py;*.pyc;*.zip"
    Dialog.Options = "ofHideReadOnly,ofEnableSizing,ofNoChangeDir,ofFileMustExist,ofDontAddToRecent"
    return Dialog.FileName if Dialog.Execute() else None  
  
class PluginManagerDialog:
    def __init__(self):
        self.Form = Gui.LoadDfmFile(os.path.dirname(__file__) + "\\PluginForm.dfm")
        Utility.TranslateProperties(self.Form._Form)
        Delta = self.Form.Label1.Width - self.Form.PathEdit.Left + 16
        self.Form.PathEdit.Width = self.Form.PathEdit.Width - Delta
        self.Form.PathEdit.Left = self.Form.PathEdit.Left + Delta
        self.Form.ListView.OnSelectItem = self.OnSelectItem
                        
        self.Form.UninstallButton.OnClick = self.OnUninstall
        self.Form.ImportButton.OnClick = self.OnImport        
        self.Refresh()
            
    def Refresh(self):        
        self.Form.ListView.Clear()
        self.Form.UninstallButton.Enabled = False
        self.Form.PathEdit.Text = ""
        self.Form.Memo.Lines.Clear()
        for Module in Graph.PluginModules:
            Item = self.Form.ListView.Items.Add()
            Item.Caption = Module.PluginName if hasattr(Module, "PluginName") else Module.__name__
            if hasattr(Module, "PluginVersion"): Item.SubItems.Add(str(Module.PluginVersion))
            Item.Data = Module
    
    def OnSelectItem(self, Sender, Item, Selected):
        Module = Item.Data
        self.Form.UninstallButton.Enabled = Selected  
        self.Form.PathEdit.Text = str(Module.__path__[0]) if Selected and hasattr(Module, "__path__") else Module.__file__
        self.Form.Memo.Lines.Text = str(Module.PluginDescription) if Selected and hasattr(Module, "PluginDescription") else ""
           
    def OnImport(self, Sender):
        PluginDir = os.environ['LOCALAPPDATA'] + "\\Graph\\Plugins"
        FileName = ShowImportDialog()
        if not FileName: return
        BaseName = os.path.basename(FileName)
        ModuleName, Ext = os.path.splitext(BaseName)
        DestPath = PluginDir + "\\" + ModuleName if Ext.lower() == ".zip" else PluginDir + "\\" + BaseName
        if os.path.exists(DestPath):
            # MB_YESNO=0x04, MB_ICONQUESTION=0x20, IDYES=6
            if vcl.Application.MessageBox(_('Plugin "%s" is already installed. Do you want to overwrite it?') % ModuleName, _("Overwrite plugin?"), 0x24) == 6:
                for Module in Graph.PluginModules[:]: 
                    if Module.__name__ == ModuleName: Graph.PluginModules.remove(Module)
            else:
                return
        try:
            if Ext.lower() == ".zip":
                with zipfile.ZipFile(FileName) as File:
                    NameList = [Name.lower() for Name in File.namelist()]
                    if not "__init__.py" in NameList and not "__init__.pyc" in NameList:
                        vcl.Application.MessageBox(_('"%s" is not a valid Graph plugin as it does not have a __init__.py file in the root.') % BaseName, _('Install failed'), 0x10) # MB_ICONSTOP=0x10
                        return
                    File.extractall(DestPath)
                Graph.LoadPlugin(PluginDir, ModuleName, True, True)
            else:
                os.makedirs(PluginDir, exist_ok=True)
                shutil.copy(FileName, PluginDir)
                Graph.LoadPlugin(PluginDir, BaseName, False, True)
        except Exception:
            Graph.Form22.Visible = True # Show Python terminal
            raise
        finally:
            self.Refresh()
        
    def OnUninstall(self, Sender):
        from . import send2trash
        import sys
        Module = self.Form.ListView.Selected.Data
        ModuleName = Module.PluginName if hasattr(Module, "PluginName") else Module.__name__
        # MB_YESNO=0x04, MB_ICONQUESTION=0x20, IDYES=6
        if vcl.Application.MessageBox(_('The plugin will keep running until Graph is closed. Are you sure you want to uninstall the plugin "%s"?') % ModuleName, _('Uninstall plugin?'), 0x24) == 6:
            Path = Module.__path__[0] if hasattr(Module, "__path__") else Module.__file__
            try:
                send2trash.send2trash(Path)
                Graph.PluginModules.remove(Module)
                del sys.modules[Module.__name__]
                self.Refresh()
            except WindowsError as E:                
                vcl.Application.MessageBox(_('Failed to uninstall the plugin "%s". You may not have access rights to delete the file.') % ModuleName, ("Uninstall failed"), 0x10) # MB_ICONSTOP=0x10
            
    def ShowModal(self):
        return self.Form.ShowModal()

def ShowPluginManager(Sender):
    global Dialog
    Dialog = PluginManagerDialog()
    Dialog.ShowModal()  
  
Action = Graph.CreateAction(Caption=_("Plugin Manager"), OnExecute=ShowPluginManager, Hint=_("Import and remove Graph plugins."), IconFile="PluginManager.png")
Graph.AddActionToMainMenu(Action)
