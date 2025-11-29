# Plugin to manage axis and graph configuration profiles
import os
import json

# Import common module
from common import show_error, show_info, Graph, vcl

PluginName = "Profile Manager"
PluginVersion = "1.0"
PluginDescription = "Saves and loads axis and graph configuration profiles."

# Directorio de perfiles
PROFILES_DIR = os.path.join(os.path.dirname(__file__), "profiles")


def font_to_dict(font):
    """Converts a VCL TFont to a serializable dictionary."""
    return {
        "name": font.Name,
        "size": font.Size,
        "color": font.Color,
        "style": list(font.Style) if font.Style else []
    }


def dict_to_font(font_dict, font):
    """Applies dictionary values to a VCL TFont."""
    if "name" in font_dict:
        font.Name = font_dict["name"]
    if "size" in font_dict:
        font.Size = font_dict["size"]
    if "color" in font_dict:
        font.Color = font_dict["color"]
    if "style" in font_dict:
        font.Style = set(font_dict["style"])


def ensure_profiles_dir():
    """Ensures that the profiles directory exists."""
    if not os.path.exists(PROFILES_DIR):
        os.makedirs(PROFILES_DIR)


def get_profile_list():
    """Gets the list of saved profiles."""
    ensure_profiles_dir()
    profiles = []
    for f in os.listdir(PROFILES_DIR):
        if f.endswith('.json'):
            profiles.append(f[:-5])  # Remove .json extension
    return sorted(profiles)


def get_current_profile():
    """Gets the current graph profile."""
    axes = Graph.Axes
    
    profile = {
        "xaxis": {
            "min": axes.xAxis.Min,
            "max": axes.xAxis.Max,
            "title": axes.xAxis.Label
        },
        "yaxis": {
            "min": axes.yAxis.Min,
            "max": axes.yAxis.Max,
            "title": axes.yAxis.Label
        },
        "config": {
            "title": axes.Title,
            "show_legend": axes.ShowLegend,
            "legend_placement": int(axes.LegendPlacement)
        },
        "fonts": {
            "label": font_to_dict(axes.LabelFont),
            "number": font_to_dict(axes.NumberFont),
            "legend": font_to_dict(axes.LegendFont),
            "title": font_to_dict(axes.TitleFont)
        }
    }
    
    return profile


def save_profile(name, profile):
    """Saves a profile to a JSON file."""
    ensure_profiles_dir()
    filepath = os.path.join(PROFILES_DIR, f"{name}.json")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


def load_profile(name):
    """Loads a profile from a JSON file."""
    filepath = os.path.join(PROFILES_DIR, f"{name}.json")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Profile '{name}' does not exist")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def apply_profile(profile):
    """Applies a profile to the current graph."""
    axes = Graph.Axes
    
    # Apply X axis configuration
    if "xaxis" in profile:
        xaxis = profile["xaxis"]
        if "min" in xaxis:
            axes.xAxis.Min = xaxis["min"]
        if "max" in xaxis:
            axes.xAxis.Max = xaxis["max"]
        if "title" in xaxis:
            axes.xAxis.Label = xaxis["title"]
    
    # Apply Y axis configuration
    if "yaxis" in profile:
        yaxis = profile["yaxis"]
        if "min" in yaxis:
            axes.yAxis.Min = yaxis["min"]
        if "max" in yaxis:
            axes.yAxis.Max = yaxis["max"]
        if "title" in yaxis:
            axes.yAxis.Label = yaxis["title"]
    
    # Apply general configuration
    if "config" in profile:
        config = profile["config"]
        if "title" in config:
            axes.Title = config["title"]
        if "show_legend" in config:
            axes.ShowLegend = config["show_legend"]
        if "legend_placement" in config:
            axes.LegendPlacement = config["legend_placement"]
    
    # Aplicar fuentes
    if "fonts" in profile:
        fonts = profile["fonts"]
        if "label" in fonts:
            dict_to_font(fonts["label"], axes.LabelFont)
        if "number" in fonts:
            dict_to_font(fonts["number"], axes.NumberFont)
        if "legend" in fonts:
            dict_to_font(fonts["legend"], axes.LegendFont)
        if "title" in fonts:
            dict_to_font(fonts["title"], axes.TitleFont)
    
    Graph.Redraw()


def manage_profiles(Action):
    """Opens the profile management dialog."""
    
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Profile Manager"
        Form.Width = 400
        Form.Height = 400
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []
        
        # Saved profiles label
        lbl_profiles = vcl.TLabel(Form)
        lbl_profiles.Parent = Form
        lbl_profiles.Caption = "Saved profiles:"
        lbl_profiles.Left = 20
        lbl_profiles.Top = 15
        lbl_profiles.Font.Style = {"fsBold"}
        labels.append(lbl_profiles)
        
        # Profile list
        lst_profiles = vcl.TListBox(Form)
        lst_profiles.Parent = Form
        lst_profiles.Left = 20
        lst_profiles.Top = 40
        lst_profiles.Width = 350
        lst_profiles.Height = 180
        
        # Load profile list
        def refresh_profile_list():
            lst_profiles.Items.Clear()
            for profile_name in get_profile_list():
                lst_profiles.Items.Add(profile_name)
        
        refresh_profile_list()
        
        # Name field
        lbl_name = vcl.TLabel(Form)
        lbl_name.Parent = Form
        lbl_name.Caption = "Name:"
        lbl_name.Left = 20
        lbl_name.Top = 235
        labels.append(lbl_name)
        
        edt_name = vcl.TEdit(Form)
        edt_name.Parent = Form
        edt_name.Left = 80
        edt_name.Top = 232
        edt_name.Width = 290
        edt_name.Text = ""
        
        # Event: when selecting a profile, load its name into the field
        def on_profile_click(Sender):
            idx = lst_profiles.ItemIndex
            if idx >= 0:
                edt_name.Text = lst_profiles.Items[idx]
        
        lst_profiles.OnClick = on_profile_click
        
        # Current profile information panel
        pnl_info = vcl.TPanel(Form)
        pnl_info.Parent = Form
        pnl_info.Left = 20
        pnl_info.Top = 265
        pnl_info.Width = 350
        pnl_info.Height = 45
        pnl_info.BevelOuter = "bvLowered"
        pnl_info.Color = 0xFFF8F0
        
        # Show current profile info
        try:
            current = get_current_profile()
            info_text = (
                f"Current: X[{current['xaxis']['min']:.2f}, {current['xaxis']['max']:.2f}] "
                f"Y[{current['yaxis']['min']:.2f}, {current['yaxis']['max']:.2f}]"
            )
        except:
            info_text = "Could not get current profile"
        
        lbl_info = vcl.TLabel(Form)
        lbl_info.Parent = pnl_info
        lbl_info.Caption = info_text
        lbl_info.Left = 10
        lbl_info.Top = 14
        lbl_info.Font.Color = 0x804000
        labels.append(lbl_info)
        
        # Buttons
        btn_save = vcl.TButton(Form)
        btn_save.Parent = Form
        btn_save.Caption = "Save Profile"
        btn_save.Left = 20
        btn_save.Top = 325
        btn_save.Width = 110
        btn_save.Height = 30
        
        btn_load = vcl.TButton(Form)
        btn_load.Parent = Form
        btn_load.Caption = "Load Profile"
        btn_load.Left = 145
        btn_load.Top = 325
        btn_load.Width = 110
        btn_load.Height = 30
        
        btn_close = vcl.TButton(Form)
        btn_close.Parent = Form
        btn_close.Caption = "Close"
        btn_close.ModalResult = 2
        btn_close.Cancel = True
        btn_close.Left = 270
        btn_close.Top = 325
        btn_close.Width = 100
        btn_close.Height = 30
        
        def on_save_click(Sender):
            name = edt_name.Text.strip()
            if not name:
                show_error("You must specify a name for the profile.", "Save Profile")
                return
            
            # Validate name (no special characters)
            invalid_chars = '<>:"/\\|?*'
            if any(c in name for c in invalid_chars):
                show_error(f"Name cannot contain: {invalid_chars}", "Save Profile")
                return
            
            try:
                profile = get_current_profile()
                save_profile(name, profile)
                refresh_profile_list()
                # show_info(f"Profile '{name}' saved successfully.", "Save Profile")
            except Exception as e:
                show_error(f"Error saving: {str(e)}", "Save Profile")
        
        def on_load_click(Sender):
            name = edt_name.Text.strip()
            if not name:
                show_error("You must specify the name of the profile to load.", "Load Profile")
                return
            
            try:
                profile = load_profile(name)
                apply_profile(profile)
                # show_info(f"Profile '{name}' loaded successfully.", "Load Profile")
                
                # Update current profile info
                try:
                    current = get_current_profile()
                    lbl_info.Caption = (
                        f"Current: X[{current['xaxis']['min']:.2f}, {current['xaxis']['max']:.2f}] "
                        f"Y[{current['yaxis']['min']:.2f}, {current['yaxis']['max']:.2f}]"
                    )
                except:
                    pass
                    
            except FileNotFoundError:
                show_error(f"Profile '{name}' does not exist.", "Load Profile")
            except Exception as e:
                show_error(f"Error loading: {str(e)}", "Load Profile")
        
        btn_save.OnClick = on_save_click
        btn_load.OnClick = on_load_click
        
        Form.ShowModal()
    
    finally:
        Form.Free()


# Create action for menu
ProfileManagerAction = Graph.CreateAction(
    Caption="Profile Manager...",
    OnExecute=manage_profiles,
    Hint="Saves and loads axis and graph configuration profiles.",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "Profile_sm.png")
)

# Add action to Plugins menu
Graph.AddActionToMainMenu(ProfileManagerAction, TopMenu="Plugins", SubMenus=["Graphîa", "Import/Export"])
