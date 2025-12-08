# Plugin to apply selective Median filter to a point series
import os

# Import common module (automatically configures venv)
from common import (
    get_selected_point_series, show_error, show_info, safe_color,
    get_series_stats, Point, Graph, vcl
)

import numpy as np
from scipy.ndimage import median_filter

PluginName = "Selective Median Filter"
PluginVersion = "1.1"
PluginDescription = "Applies a median filter only to points that deviate significantly from their neighborhood."


def apply_median_filter(Action):
    """Applies a selective median filter to the selected point series."""
    
    # Check that a TPointSeries is selected
    point_series, error_msg = get_selected_point_series()
    
    if point_series is None:
        show_error(error_msg, "Median Filter")
        return
    
    # Verify the series has points
    points = point_series.Points
    if not points or len(points) < 5:
        show_error(
            "The point series must have at least 5 points to apply the filter.",
            "Median Filter"
        )
        return
    
    # Get series statistics
    stats = get_series_stats(point_series)
    x_vals = stats['x_vals']
    y_vals = np.array(stats['y_vals'])
    y_min, y_max = stats['y_min'], stats['y_max']
    y_range = stats['y_range']
    n_points = stats['n_points']
    
    # Suggested value for threshold (based on standard deviation)
    y_std = np.std(y_vals)
    suggested_threshold = y_std * 2
    
    # Create configuration form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Selective Median Filter"
        Form.Width = 450
        Form.Height = 520
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
        
        # Range information
        lbl_range = vcl.TLabel(Form)
        lbl_range.Parent = Form
        lbl_range.Caption = f"Y Range: [{y_min:.4g}, {y_max:.4g}]  |  σ = {y_std:.4g}"
        lbl_range.Left = 20
        lbl_range.Top = 35
        lbl_range.Font.Color = 0x666666
        labels.append(lbl_range)
        
        # Separador visual
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 55
        sep1.Width = 420
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Window size (kernel)
        lbl_kernel = vcl.TLabel(Form)
        lbl_kernel.Parent = Form
        lbl_kernel.Caption = "Window size (points):"
        lbl_kernel.Left = 20
        lbl_kernel.Top = 70
        labels.append(lbl_kernel)
        
        edit_kernel = vcl.TEdit(Form)
        edit_kernel.Parent = Form
        edit_kernel.Left = 200
        edit_kernel.Top = 67
        edit_kernel.Width = 60
        edit_kernel.Text = "5"
        
        lbl_kernel_hint = vcl.TLabel(Form)
        lbl_kernel_hint.Parent = Form
        lbl_kernel_hint.Caption = "(odd, ≥3)"
        lbl_kernel_hint.Left = 270
        lbl_kernel_hint.Top = 70
        lbl_kernel_hint.Font.Color = 0x808080
        labels.append(lbl_kernel_hint)
        
        # Deviation threshold
        lbl_thresh = vcl.TLabel(Form)
        lbl_thresh.Parent = Form
        lbl_thresh.Caption = "Deviation threshold:"
        lbl_thresh.Left = 20
        lbl_thresh.Top = 105
        labels.append(lbl_thresh)
        
        edit_thresh = vcl.TEdit(Form)
        edit_thresh.Parent = Form
        edit_thresh.Left = 200
        edit_thresh.Top = 102
        edit_thresh.Width = 100
        edit_thresh.Text = f"{suggested_threshold:.4g}"
        
        # Help panel
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 20
        help_panel.Top = 140
        help_panel.Width = 400
        help_panel.Height = 130
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0  # Light blue background
        
        lbl_help_title = vcl.TLabel(Form)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "How does it work?"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)
        
        help_text = (
            f"1. For each point, the neighborhood median is calculated\n"
            f"2. If |value - median| > threshold, it's replaced by median\n"
            f"3. Points within threshold are NOT modified\n"
            f"\n"
            f"• Ideal for removing spikes while preserving original signal\n"
            f"• Suggested threshold (2σ): {suggested_threshold:.4g}"
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
        lbl_option.Top = 285
        labels.append(lbl_option)
        
        rb_new = vcl.TRadioButton(Form)
        rb_new.Parent = Form
        rb_new.Caption = "Create new series"
        rb_new.Left = 120
        rb_new.Top = 285
        rb_new.Checked = True
        
        rb_replace = vcl.TRadioButton(Form)
        rb_replace.Parent = Form
        rb_replace.Caption = "Replace original series"
        rb_replace.Left = 120
        rb_replace.Top = 310
        
        # Color for new series
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Color (new series):"
        lbl_color.Left = 20
        lbl_color.Top = 350
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 150
        cb_color.Top = 347
        cb_color.Width = 100
        cb_color.Selected = 0xFF00FF  # Magenta por defecto
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Apply"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 100
        btn_ok.Top = 400
        btn_ok.Width = 100
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 240
        btn_cancel.Top = 400
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # Show dialog
        if Form.ShowModal() == 1:
            try:
                kernel_size = int(edit_kernel.Text)
                threshold = float(edit_thresh.Text)
                
                if kernel_size < 3:
                    raise ValueError("Window size must be at least 3")
                
                # Asegurar que sea impar
                if kernel_size % 2 == 0:
                    kernel_size += 1
                
                if threshold <= 0:
                    raise ValueError("El umbral debe ser mayor que 0")
                
                # Calcular mediana de la vecindad para cada punto
                y_median = median_filter(y_vals, size=kernel_size, mode='nearest')
                
                # Calculate deviation of each point from local median
                deviation = np.abs(y_vals - y_median)
                
                # Create filtered signal: only replace points exceeding threshold
                y_filtered = y_vals.copy()
                outlier_mask = deviation > threshold
                y_filtered[outlier_mask] = y_median[outlier_mask]
                
                n_modified = np.sum(outlier_mask)
                
                # Crear nuevos puntos
                new_points = [Point(x, y) for x, y in zip(x_vals, y_filtered)]
                
                if rb_new.Checked:
                    # Crear nueva serie
                    new_series = Graph.TPointSeries()
                    new_series.PointType = point_series.PointType
                    new_series.Points = new_points
                    
                    # Copy display properties
                    original_legend = point_series.LegendText
                    new_series.LegendText = f"{original_legend} [Median k={kernel_size}, th={threshold:.3g}]"
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
                    if "[Median" not in original_legend:
                        point_series.LegendText = f"{original_legend} [Median k={kernel_size}]"
                
                Graph.Update()
                
                # Show summary
                show_info(
                    f"Filter applied successfully.\n\nPoints modified: {n_modified} of {n_points} ({100*n_modified/n_points:.1f}%)",
                    "Median Filter"
                )
                
            except ValueError as e:
                show_error(f"Parameter error: {str(e)}", "Median Filter")
            except Exception as e:
                show_error(f"Error applying filter: {str(e)}", "Median Filter")
    finally:
        Form.Free()


# Create action for menu
MedianFilterAction = Graph.CreateAction(
    Caption="Median Filter...",
    OnExecute=apply_median_filter,
    Hint="Applies a selective median filter to remove outliers/spikes.",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "Median_sm.png")
)

# Add action to 'Smoothing' submenu within 'Plugins'
Graph.AddActionToMainMenu(MedianFilterAction, TopMenu="Plugins", SubMenus=["Graphîa", "Smoothing"])
