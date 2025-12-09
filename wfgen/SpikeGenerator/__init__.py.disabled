# Plugin to add spikes (noise peaks) to a point series
import os

# Import common module (automatically configures venv)
from common import (
    get_selected_point_series, show_error, safe_color,
    get_series_stats, Point, Graph, vcl
)

import numpy as np

PluginName = "Spike Generator"
PluginVersion = "1.1"
PluginDescription = "Adds random noise spikes to the selected point series."


def add_spikes(Action):
    """Adds random spikes to the selected point series."""
    
    # Check that a TPointSeries is selected
    point_series, error_msg = get_selected_point_series()
    
    if point_series is None:
        show_error(error_msg, "Spike Generator")
        return
    
    # Verify the series has points
    points = point_series.Points
    if not points or len(points) < 3:
        show_error(
            "The point series must have at least 3 points.",
            "Spike Generator"
        )
        return
    
    # Get series statistics
    stats = get_series_stats(point_series)
    y_vals = stats['y_vals']
    y_min, y_max = stats['y_min'], stats['y_max']
    y_range = stats['y_range']
    n_points = stats['n_points']
    
    # Valores sugeridos para amplitud de spikes
    suggested_min_amp = y_max + y_range * 0.2
    suggested_max_amp = y_max + y_range * 0.5
    
    # Create configuration form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Spike Generator"
        Form.Width = 420
        Form.Height = 480
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []  # Keep references
        
        # Series information
        lbl_info = vcl.TLabel(Form)
        lbl_info.Parent = Form
        lbl_info.Caption = f"Selected series: {n_points} points"
        lbl_info.Left = 20
        lbl_info.Top = 15
        lbl_info.Font.Style = {"fsBold"}
        labels.append(lbl_info)
        
        # Y range information
        lbl_range = vcl.TLabel(Form)
        lbl_range.Parent = Form
        lbl_range.Caption = f"Y Range: [{y_min:.4g}, {y_max:.4g}]"
        lbl_range.Left = 20
        lbl_range.Top = 35
        lbl_range.Font.Color = 0x666666
        labels.append(lbl_range)
        
        # Separador visual
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 55
        sep1.Width = 390
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Spike proportion
        lbl_prop = vcl.TLabel(Form)
        lbl_prop.Parent = Form
        lbl_prop.Caption = "Spike proportion (%):"
        lbl_prop.Left = 20
        lbl_prop.Top = 70
        labels.append(lbl_prop)
        
        edit_prop = vcl.TEdit(Form)
        edit_prop.Parent = Form
        edit_prop.Left = 180
        edit_prop.Top = 67
        edit_prop.Width = 60
        edit_prop.Text = "5"
        
        lbl_prop_info = vcl.TLabel(Form)
        lbl_prop_info.Parent = Form
        lbl_prop_info.Caption = f"(≈ {int(n_points * 0.05)} points)"
        lbl_prop_info.Left = 250
        lbl_prop_info.Top = 70
        lbl_prop_info.Font.Color = 0x808080
        labels.append(lbl_prop_info)
        
        # Minimum spike amplitude
        lbl_min_amp = vcl.TLabel(Form)
        lbl_min_amp.Parent = Form
        lbl_min_amp.Caption = "Min spike amplitude:"
        lbl_min_amp.Left = 20
        lbl_min_amp.Top = 105
        labels.append(lbl_min_amp)
        
        edit_min_amp = vcl.TEdit(Form)
        edit_min_amp.Parent = Form
        edit_min_amp.Left = 180
        edit_min_amp.Top = 102
        edit_min_amp.Width = 100
        edit_min_amp.Text = f"{suggested_min_amp:.4g}"
        
        # Maximum spike amplitude
        lbl_max_amp = vcl.TLabel(Form)
        lbl_max_amp.Parent = Form
        lbl_max_amp.Caption = "Max spike amplitude:"
        lbl_max_amp.Left = 20
        lbl_max_amp.Top = 140
        labels.append(lbl_max_amp)
        
        edit_max_amp = vcl.TEdit(Form)
        edit_max_amp.Parent = Form
        edit_max_amp.Left = 180
        edit_max_amp.Top = 137
        edit_max_amp.Width = 100
        edit_max_amp.Text = f"{suggested_max_amp:.4g}"
        
        # Help panel
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 20
        help_panel.Top = 175
        help_panel.Width = 370
        help_panel.Height = 85
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xF0FFF0  # Light green background
        
        lbl_help_title = vcl.TLabel(Form)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Information:"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x006400
        labels.append(lbl_help_title)
        
        help_text = (
            f"• Spikes replace Y values at random points\n"
            f"• Uniform amplitude between [min, max]\n"
            f"• Current signal range: {y_range:.4g}\n"
            f"• Suggested: amplitudes outside range to stand out"
        )
        
        lbl_help = vcl.TLabel(Form)
        lbl_help.Parent = help_panel
        lbl_help.Caption = help_text
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x006400
        labels.append(lbl_help)
        
        # Option: create new series or modify existing
        lbl_option = vcl.TLabel(Form)
        lbl_option.Parent = Form
        lbl_option.Caption = "Output:"
        lbl_option.Left = 20
        lbl_option.Top = 275
        labels.append(lbl_option)
        
        rb_new = vcl.TRadioButton(Form)
        rb_new.Parent = Form
        rb_new.Caption = "Create new series"
        rb_new.Left = 120
        rb_new.Top = 275
        rb_new.Checked = True
        
        rb_replace = vcl.TRadioButton(Form)
        rb_replace.Parent = Form
        rb_replace.Caption = "Replace original series"
        rb_replace.Left = 120
        rb_replace.Top = 300
        
        # Color for new series
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Color (new series):"
        lbl_color.Left = 20
        lbl_color.Top = 340
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 150
        cb_color.Top = 337
        cb_color.Width = 100
        cb_color.Selected = 0x00AA00  # Verde por defecto
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Apply"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 90
        btn_ok.Top = 390
        btn_ok.Width = 100
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 220
        btn_cancel.Top = 390
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # Show dialog
        if Form.ShowModal() == 1:
            try:
                prop_noise = float(edit_prop.Text) / 100.0
                min_spike_amp = float(edit_min_amp.Text)
                max_spike_amp = float(edit_max_amp.Text)
                
                if prop_noise <= 0 or prop_noise > 100:
                    raise ValueError("Proportion must be between 0 and 100%")
                
                if min_spike_amp > max_spike_amp:
                    raise ValueError("Min amplitude must be less than or equal to max")
                
                # Extraer valores X e Y
                x_vals = np.array(stats['x_vals'])
                y_vals_np = np.array(y_vals)
                
                # Select random points for spikes
                n = len(y_vals_np)
                n_spikes = int(n * prop_noise)
                
                if n_spikes < 1:
                    raise ValueError("Proportion too low, no spikes would be generated")
                
                noise_pnts = np.random.permutation(n)
                noise_pnts = noise_pnts[:n_spikes]
                
                # Generar spikes con amplitud aleatoria uniforme
                spike_values = min_spike_amp + np.random.rand(n_spikes) * (max_spike_amp - min_spike_amp)
                
                # Aplicar spikes
                y_with_spikes = y_vals_np.copy()
                y_with_spikes[noise_pnts] += spike_values
                
                # Crear nuevos puntos
                new_points = [Point(x, y) for x, y in zip(x_vals, y_with_spikes)]
                
                if rb_new.Checked:
                    # Crear nueva serie
                    new_series = Graph.TPointSeries()
                    new_series.PointType = point_series.PointType
                    new_series.Points = new_points
                    
                    # Copy display properties
                    original_legend = point_series.LegendText
                    new_series.LegendText = f"{original_legend} [+spikes {prop_noise*100:.1f}%]"
                    new_series.Size = point_series.Size
                    new_series.Style = point_series.Style
                    new_series.LineSize = point_series.LineSize
                    new_series.ShowLabels = point_series.ShowLabels
                    
                    # Usar el color seleccionado
                    color_val = safe_color(cb_color.Selected)
                    new_series.FillColor = color_val
                    new_series.FrameColor = color_val
                    new_series.LineColor = color_val
                    
                    Graph.FunctionList.append(new_series)
                else:
                    # Reemplazar puntos en la serie original
                    point_series.Points = new_points
                    original_legend = point_series.LegendText
                    if "[+spikes" not in original_legend:
                        point_series.LegendText = f"{original_legend} [+spikes {prop_noise*100:.1f}%]"
                
                Graph.Update()
                
            except ValueError as e:
                show_error(f"Parameter error: {str(e)}", "Spike Generator")
            except Exception as e:
                show_error(f"Error generating spikes: {str(e)}", "Spike Generator")
    finally:
        Form.Free()


# Create action for menu
SpikeGeneratorAction = Graph.CreateAction(
    Caption="Spike Generator...",
    IconFile=os.path.join(os.path.dirname(__file__), "Spike_sm.png"),
    OnExecute=add_spikes,
    Hint="Adds random noise spikes to the selected point series.",
    ShortCut=""
)

# Add action to 'AWF Generators' submenu within 'Plugins'
Graph.AddActionToMainMenu(SpikeGeneratorAction, TopMenu="Plugins", SubMenus=["Graphîa", "AWF Generators"])
