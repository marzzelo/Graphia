# Plugin to apply Gaussian filter to point series
import os

# Import common module (automatically configures venv)
from common import (
    get_selected_point_series, show_error, safe_color,
    get_series_stats, Point, Graph, vcl
)

from scipy.ndimage import gaussian_filter1d

PluginName = "Gaussian Filter"
PluginVersion = "1.2"
PluginDescription = "Applies a Gaussian filter (smoothing) to the selected point series."


def apply_gaussian_filter(Action):
    """Applies a Gaussian filter to the selected point series."""
    
    # Check that a TPointSeries is selected
    point_series, error_msg = get_selected_point_series()
    
    if point_series is None:
        show_error(error_msg, "Gaussian Filter")
        return
    
    # Verify the series has points
    points = point_series.Points
    if not points or len(points) < 3:
        show_error(
            "The point series must have at least 3 points to apply the filter.",
            "Gaussian Filter"
        )
        return
    
    # Get series statistics
    stats = get_series_stats(point_series)
    x_vals = stats['x_vals']
    x_min, x_max = stats['x_min'], stats['x_max']
    x_range = stats['x_range']
    dx_avg = stats['dx_avg']
    
    # Valor sugerido de sigma: ~1% del rango X
    sigma_suggested = x_range * 0.01
    
    # Create configuration form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Gaussian Filter"
        Form.Width = 400
        Form.Height = 510
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []  # Keep references
        
        # Series information
        lbl_info = vcl.TLabel(Form)
        lbl_info.Parent = Form
        lbl_info.Caption = f"Selected series: {len(points)} points"
        lbl_info.Left = 20
        lbl_info.Top = 15
        lbl_info.Font.Style = {"fsBold"}
        labels.append(lbl_info)
        
        # X range information
        lbl_range = vcl.TLabel(Form)
        lbl_range.Parent = Form
        lbl_range.Caption = f"t Range: [{x_min:.4g}, {x_max:.4g}]  |  Avg Δt: {dx_avg:.4g}"
        lbl_range.Left = 20
        lbl_range.Top = 35
        lbl_range.Font.Color = 0x666666
        labels.append(lbl_range)
        
        # Separador visual
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 55
        sep1.Width = 370
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Sigma (Gaussian kernel standard deviation)
        lbl_sigma = vcl.TLabel(Form)
        lbl_sigma.Parent = Form
        lbl_sigma.Caption = "Sigma (σ) in t units:"
        lbl_sigma.Left = 20
        lbl_sigma.Top = 70
        labels.append(lbl_sigma)
        
        edit_sigma = vcl.TEdit(Form)
        edit_sigma.Parent = Form
        edit_sigma.Left = 180
        edit_sigma.Top = 67
        edit_sigma.Width = 100
        edit_sigma.Text = f"{sigma_suggested:.4g}"
        
        # Edge extension mode
        lbl_mode = vcl.TLabel(Form)
        lbl_mode.Parent = Form
        lbl_mode.Caption = "Edge mode:"
        lbl_mode.Left = 20
        lbl_mode.Top = 100
        labels.append(lbl_mode)
        
        cb_mode = vcl.TComboBox(Form)
        cb_mode.Parent = Form
        cb_mode.Left = 180
        cb_mode.Top = 97
        cb_mode.Width = 120
        cb_mode.Style = "csDropDownList"
        cb_mode.Items.Add("nearest")
        cb_mode.Items.Add("reflect")
        cb_mode.Items.Add("mirror")
        cb_mode.Items.Add("wrap")
        cb_mode.Items.Add("constant")
        cb_mode.ItemIndex = 0  # nearest por defecto
        
        # Truncate (number of standard deviations)
        lbl_truncate = vcl.TLabel(Form)
        lbl_truncate.Parent = Form
        lbl_truncate.Caption = "Truncate at (σ):"
        lbl_truncate.Left = 20
        lbl_truncate.Top = 130
        labels.append(lbl_truncate)
        
        edit_truncate = vcl.TEdit(Form)
        edit_truncate.Parent = Form
        edit_truncate.Left = 180
        edit_truncate.Top = 127
        edit_truncate.Width = 60
        edit_truncate.Text = "4.0"
        
        # Help panel for sigma
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 20
        help_panel.Top = 160
        help_panel.Width = 350
        help_panel.Height = 145
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0  # Light blue background
        
        lbl_help_title = vcl.TLabel(Form)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Parameter guide:"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)
        
        help_text = (
            f"σ (sigma): Smoothing width in t units\n"
            f"  • Variations < 2σ attenuated, > 2σ preserved\n"
            f"  • Suggested (1% of {x_range:.4g}): {sigma_suggested:.4g}\n"
            f"Mode: How to extend the signal at edges\n"
            f"  • nearest: repeats edge value\n"
            f"  • reflect/mirror: reflects the signal\n"
            f"Truncate: Limits kernel to N std deviations\n"
            f"  • Lower value = faster, less precise"
        )
        
        lbl_help = vcl.TLabel(Form)
        lbl_help.Parent = help_panel
        lbl_help.Caption = help_text
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)
        
        # Option: create new series or modify existing
        lbl_option = vcl.TLabel(Form)
        lbl_option.Parent = Form
        lbl_option.Caption = "Output:"
        lbl_option.Left = 20
        lbl_option.Top = 320
        labels.append(lbl_option)
        
        rb_new = vcl.TRadioButton(Form)
        rb_new.Parent = Form
        rb_new.Caption = "Create new series"
        rb_new.Left = 120
        rb_new.Top = 320
        rb_new.Checked = True
        
        rb_replace = vcl.TRadioButton(Form)
        rb_replace.Parent = Form
        rb_replace.Caption = "Replace original series"
        rb_replace.Left = 120
        rb_replace.Top = 345
        
        # Color for new series
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Color (new series):"
        lbl_color.Left = 20
        lbl_color.Top = 380
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 140
        cb_color.Top = 377
        cb_color.Width = 100
        cb_color.Selected = 0x0000FF  # Rojo por defecto
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Apply"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 80
        btn_ok.Top = 430
        btn_ok.Width = 100
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 210
        btn_cancel.Top = 430
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # Show dialog
        if Form.ShowModal() == 1:
            try:
                sigma_x = float(edit_sigma.Text)
                truncate_val = float(edit_truncate.Text)
                mode_val = cb_mode.Text
                
                if sigma_x <= 0:
                    raise ValueError("Sigma debe ser mayor que 0")
                
                if truncate_val <= 0:
                    raise ValueError("Truncar debe ser mayor que 0")
                
                # Extract Y values (X already in x_vals)
                y_vals = [p.y for p in points]
                
                # Convert sigma from X units to number of points
                sigma_points = sigma_x / dx_avg if dx_avg > 0 else sigma_x
                
                # Aplicar filtro Gaussiano a los valores Y
                y_filtered = gaussian_filter1d(y_vals, sigma=sigma_points, mode=mode_val, truncate=truncate_val)
                
                # Crear nuevos puntos
                new_points = [Point(x, y) for x, y in zip(x_vals, y_filtered)]
                
                if rb_new.Checked:
                    # Crear nueva serie
                    new_series = Graph.TPointSeries()
                    new_series.PointType = point_series.PointType
                    new_series.Points = new_points
                    
                    # Copy display properties
                    original_legend = point_series.LegendText
                    new_series.LegendText = f"{original_legend} [Gaussian σ={sigma_x}]"
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
                    if "[Gaussian" not in original_legend:
                        point_series.LegendText = f"{original_legend} [Gaussian σ={sigma_x}]"
                
                Graph.Update()
                
            except ValueError as e:
                show_error(f"Parameter error: {str(e)}", "Gaussian Filter")
            except Exception as e:
                show_error(f"Error applying filter: {str(e)}", "Gaussian Filter")
    finally:
        Form.Free()


# Create action for menu
GaussianFilterAction = Graph.CreateAction(
    Caption="Gaussian Filter...",
    OnExecute=apply_gaussian_filter,
    Hint="Applies a Gaussian filter (smoothing) to the selected point series.",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "Gaussian_sm.png")
)

# Add action to 'Smoothing' submenu within 'Plugins'
Graph.AddActionToMainMenu(GaussianFilterAction, TopMenu="Plugins", SubMenus=["Graphîa", "Smoothing"])
