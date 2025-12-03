"""
Histogram - Plugin to generate histogram curve from point series
Uses numpy.histogram to compute the histogram of Y values.
"""

import Graph
import vcl  # type: ignore
import os

# Import common utilities
from common import (
    setup_venv, get_selected_point_series, show_error, show_info, 
    get_series_data, Point, safe_color
)

# Import numpy
import numpy as np

PluginName = "Histogram"
PluginVersion = "1.0"
PluginDescription = "Generate histogram curve from Y values of the selected point series."


def histogram_dialog(Action):
    """
    Shows a dialog to configure and generate a histogram from the selected series.
    """
    # Get selected series
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "Histogram")
        return

    # Get current data
    x_vals, y_vals = get_series_data(series)
    
    if not y_vals:
        show_info("The selected series has no points.", "Histogram")
        return

    # Calculate stats for info
    y_arr = np.array(y_vals)
    y_min = float(np.min(y_arr))
    y_max = float(np.max(y_arr))
    n_points = len(y_vals)
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Histogram"
        Form.Width = 450
        Form.Height = 420
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []  # Keep references
        
        # =====================================================================
        # Help panel at top
        # =====================================================================
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 10
        help_panel.Top = 10
        help_panel.Width = 420
        help_panel.Height = 55
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0

        lbl_help_title = vcl.TLabel(help_panel)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Histogram Generator"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        lbl_help = vcl.TLabel(help_panel)
        lbl_help.Parent = help_panel
        lbl_help.Caption = f"Series: {series.LegendText if series.LegendText else '(unnamed)'}  |  {n_points} points  |  Y ∈ [{y_min:.4g}, {y_max:.4g}]"
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)

        # =====================================================================
        # Parameters Section
        # =====================================================================
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 75
        sep1.Width = 420
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        lbl_params = vcl.TLabel(Form)
        lbl_params.Parent = Form
        lbl_params.Caption = "Histogram Parameters"
        lbl_params.Left = 10
        lbl_params.Top = 85
        lbl_params.Font.Style = {"fsBold"}
        labels.append(lbl_params)
        
        # Panel for parameters
        pnl_params = vcl.TPanel(Form)
        pnl_params.Parent = Form
        pnl_params.Left = 10
        pnl_params.Top = 108
        pnl_params.Width = 420
        pnl_params.Height = 130
        pnl_params.BevelOuter = "bvLowered"
        
        # Bins
        lbl_bins = vcl.TLabel(Form)
        lbl_bins.Parent = pnl_params
        lbl_bins.Caption = "Bins:"
        lbl_bins.Left = 15
        lbl_bins.Top = 15
        labels.append(lbl_bins)
        
        edt_bins = vcl.TEdit(Form)
        edt_bins.Parent = pnl_params
        edt_bins.Left = 100
        edt_bins.Top = 12
        edt_bins.Width = 80
        edt_bins.Text = "10"
        
        lbl_bins_info = vcl.TLabel(Form)
        lbl_bins_info.Parent = pnl_params
        lbl_bins_info.Caption = "Number of equal-width bins"
        lbl_bins_info.Left = 190
        lbl_bins_info.Top = 15
        lbl_bins_info.Font.Color = 0x666666
        labels.append(lbl_bins_info)
        
        # Range Min
        lbl_range_min = vcl.TLabel(Form)
        lbl_range_min.Parent = pnl_params
        lbl_range_min.Caption = "Range Min:"
        lbl_range_min.Left = 15
        lbl_range_min.Top = 45
        labels.append(lbl_range_min)
        
        edt_range_min = vcl.TEdit(Form)
        edt_range_min.Parent = pnl_params
        edt_range_min.Left = 100
        edt_range_min.Top = 42
        edt_range_min.Width = 80
        edt_range_min.Text = f"{y_min:.6g}"
        
        lbl_range_min_info = vcl.TLabel(Form)
        lbl_range_min_info.Parent = pnl_params
        lbl_range_min_info.Caption = f"(data min: {y_min:.4g})"
        lbl_range_min_info.Left = 190
        lbl_range_min_info.Top = 45
        lbl_range_min_info.Font.Color = 0x666666
        labels.append(lbl_range_min_info)
        
        # Range Max
        lbl_range_max = vcl.TLabel(Form)
        lbl_range_max.Parent = pnl_params
        lbl_range_max.Caption = "Range Max:"
        lbl_range_max.Left = 15
        lbl_range_max.Top = 75
        labels.append(lbl_range_max)
        
        edt_range_max = vcl.TEdit(Form)
        edt_range_max.Parent = pnl_params
        edt_range_max.Left = 100
        edt_range_max.Top = 72
        edt_range_max.Width = 80
        edt_range_max.Text = f"{y_max:.6g}"
        
        lbl_range_max_info = vcl.TLabel(Form)
        lbl_range_max_info.Parent = pnl_params
        lbl_range_max_info.Caption = f"(data max: {y_max:.4g})"
        lbl_range_max_info.Left = 190
        lbl_range_max_info.Top = 75
        lbl_range_max_info.Font.Color = 0x666666
        labels.append(lbl_range_max_info)
        
        # Density checkbox
        chk_density = vcl.TCheckBox(Form)
        chk_density.Parent = pnl_params
        chk_density.Caption = "Density (normalize so that integral = 1)"
        chk_density.Left = 15
        chk_density.Top = 105
        chk_density.Width = 300
        chk_density.Checked = False
        
        # =====================================================================
        # Output Section
        # =====================================================================
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 248
        sep2.Width = 420
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output"
        lbl_output.Left = 10
        lbl_output.Top = 258
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Color selector
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Histogram Color:"
        lbl_color.Left = 20
        lbl_color.Top = 285
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 130
        cb_color.Top = 282
        cb_color.Width = 100
        cb_color.Selected = 0x0066CC  # Orange-ish by default
        
        # Plot style
        lbl_style = vcl.TLabel(Form)
        lbl_style.Parent = Form
        lbl_style.Caption = "Plot Style:"
        lbl_style.Left = 250
        lbl_style.Top = 285
        labels.append(lbl_style)
        
        cmb_style = vcl.TComboBox(Form)
        cmb_style.Parent = Form
        cmb_style.Left = 320
        cmb_style.Top = 282
        cmb_style.Width = 100
        cmb_style.Style = "csDropDownList"
        cmb_style.Items.Add("Steps")
        cmb_style.Items.Add("Bars (centers)")
        cmb_style.ItemIndex = 0
        
        # =====================================================================
        # Buttons
        # =====================================================================
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 325
        sep3.Width = 420
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        btn_generate = vcl.TButton(Form)
        btn_generate.Parent = Form
        btn_generate.Caption = "Generate"
        btn_generate.Left = 130
        btn_generate.Top = 345
        btn_generate.Width = 100
        btn_generate.Height = 30
        btn_generate.Default = True
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 240
        btn_cancel.Top = 345
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        def on_generate(Sender):
            try:
                # Parse parameters
                try:
                    bins = int(edt_bins.Text)
                    if bins < 1:
                        raise ValueError("Bins must be >= 1")
                except ValueError as e:
                    show_error(f"Invalid bins value: {e}", "Histogram")
                    return
                
                try:
                    range_min = float(edt_range_min.Text)
                    range_max = float(edt_range_max.Text)
                    if range_max <= range_min:
                        raise ValueError("Range max must be greater than range min")
                except ValueError as e:
                    show_error(f"Invalid range value: {e}", "Histogram")
                    return
                
                density = chk_density.Checked
                
                # Compute histogram
                hist_range = (range_min, range_max)
                counts, bin_edges = np.histogram(y_arr, bins=bins, range=hist_range, density=density)
                
                # Create points based on style
                style_idx = cmb_style.ItemIndex
                
                if style_idx == 0:  # Steps style
                    # Create step plot: for each bin, two points at the same height
                    points = []
                    for i in range(len(counts)):
                        left_edge = bin_edges[i]
                        right_edge = bin_edges[i + 1]
                        height = counts[i]
                        points.append(Point(left_edge, height))
                        points.append(Point(right_edge, height))
                else:  # Bars (centers) style
                    # Use bin centers
                    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                    points = [Point(x, y) for x, y in zip(bin_centers, counts)]
                
                # Create series
                hist_series = Graph.TPointSeries()
                hist_series.Points = points
                
                # Legend
                original_legend = series.LegendText if series.LegendText else "Series"
                density_str = ", density" if density else ""
                hist_series.LegendText = f"{original_legend} [Histogram, {bins} bins{density_str}]"
                
                # Style
                hist_series.Size = 0 if style_idx == 0 else 3
                hist_series.Style = 0
                hist_series.LineSize = 2
                hist_series.ShowLabels = False
                
                # Color
                color_val = safe_color(cb_color.Selected)
                hist_series.FillColor = color_val
                hist_series.FrameColor = color_val
                hist_series.LineColor = color_val
                
                # Add to graph
                Graph.FunctionList.append(hist_series)
                Graph.Update()
                
                show_info(f"Histogram generated with {bins} bins.", "Histogram")
                
            except Exception as e:
                show_error(f"Error generating histogram: {str(e)}", "Histogram")
        
        btn_generate.OnClick = on_generate
        
        # Show dialog
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="Histogram...", 
    OnExecute=histogram_dialog, 
    Hint="Generate histogram curve from Y values of the selected series",
    IconFile=os.path.join(os.path.dirname(__file__), "Histogram_sm.png")
)

# Add to Plugins -> Analysis menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Analysis"])
