# Plugin to fill a segment of a point series with constant values or values from another series
import os

# Import common module
from common import (
    get_selected_point_series, get_all_point_series, show_error, show_info,
    safe_color, Point, Graph, vcl, get_series_data_np
)

import numpy as np

PluginName = "Fill Segment"
PluginVersion = "1.0"
PluginDescription = "Fills a segment of a point series with constant values or values from another series."

# Fill modes
FILL_MODE_CONSTANT = 0
FILL_MODE_FROM_SERIES = 1


def interpolate_series_values(x_target, x_source, y_source):
    """
    Interpolates values from source series to match target X values.
    Uses linear interpolation.
    
    Args:
        x_target: X values where we need Y values
        x_source: X values of source series
        y_source: Y values of source series
    
    Returns:
        numpy array of interpolated Y values
    """
    return np.interp(x_target, x_source, y_source, left=np.nan, right=np.nan)


def fill_segment(Action):
    """Fills a segment of the selected point series."""
    
    # Get selected series
    point_series, error_msg = get_selected_point_series()
    if point_series is None:
        show_error(error_msg or "You must select a point series (TPointSeries).", "Fill Segment")
        return
    
    # Get original data
    x_orig, y_orig = get_series_data_np(point_series)
    if len(x_orig) < 2:
        show_error("The series must have at least 2 points.", "Fill Segment")
        return
    
    # Get all other series for the dropdown
    all_series = get_all_point_series()
    other_series = [s for s in all_series if s != point_series]
    
    # Calculate series info
    x_min, x_max = float(x_orig.min()), float(x_orig.max())
    n_points = len(x_orig)
    dx = np.diff(x_orig)
    current_period = float(np.mean(dx))
    
    # Get visible window limits (default for Start X / End X)
    view_x_min = Graph.Axes.xAxis.Min
    view_x_max = Graph.Axes.xAxis.Max
    
    # Clamp to series range
    default_start = max(view_x_min, x_min)
    default_end = min(view_x_max, x_max)
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Fill Segment"
        Form.Width = 450
        Form.Height = 520
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []
        
        # Original series info
        lbl_info = vcl.TLabel(Form)
        lbl_info.Parent = Form
        lbl_info.Caption = "Selected series:"
        lbl_info.Left = 20
        lbl_info.Top = 15
        lbl_info.Font.Style = {"fsBold"}
        labels.append(lbl_info)
        
        lbl_series_name = vcl.TLabel(Form)
        lbl_series_name.Parent = Form
        lbl_series_name.Caption = point_series.LegendText or "(unnamed)"
        lbl_series_name.Left = 130
        lbl_series_name.Top = 15
        lbl_series_name.Font.Color = 0x666666
        labels.append(lbl_series_name)
        
        info_text = (
            f"Points: {n_points}  |  "
            f"X: [{x_min:.4g}, {x_max:.4g}]  |  "
            f"Ts ≈ {current_period:.4g}"
        )
        lbl_info_val = vcl.TLabel(Form)
        lbl_info_val.Parent = Form
        lbl_info_val.Caption = info_text
        lbl_info_val.Left = 20
        lbl_info_val.Top = 35
        lbl_info_val.Font.Color = 0x888888
        labels.append(lbl_info_val)
        
        # Separador
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 58
        sep1.Width = 420
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # === Segment range ===
        lbl_range = vcl.TLabel(Form)
        lbl_range.Parent = Form
        lbl_range.Caption = "Segment to fill:"
        lbl_range.Left = 20
        lbl_range.Top = 75
        lbl_range.Font.Style = {"fsBold"}
        labels.append(lbl_range)
        
        lbl_start = vcl.TLabel(Form)
        lbl_start.Parent = Form
        lbl_start.Caption = "Start X:"
        lbl_start.Left = 20
        lbl_start.Top = 100
        labels.append(lbl_start)
        
        edt_start = vcl.TEdit(Form)
        edt_start.Parent = Form
        edt_start.Left = 80
        edt_start.Top = 97
        edt_start.Width = 100
        edt_start.Text = f"{default_start:.6g}"
        
        lbl_end = vcl.TLabel(Form)
        lbl_end.Parent = Form
        lbl_end.Caption = "End X:"
        lbl_end.Left = 200
        lbl_end.Top = 100
        labels.append(lbl_end)
        
        edt_end = vcl.TEdit(Form)
        edt_end.Parent = Form
        edt_end.Left = 260
        edt_end.Top = 97
        edt_end.Width = 100
        edt_end.Text = f"{default_end:.6g}"
        
        # Points in range info
        lbl_points_in_range = vcl.TLabel(Form)
        lbl_points_in_range.Parent = Form
        lbl_points_in_range.Caption = f"({n_points} points in range)"
        lbl_points_in_range.Left = 370
        lbl_points_in_range.Top = 100
        lbl_points_in_range.Font.Color = 0x808080
        labels.append(lbl_points_in_range)
        
        # === Fill mode ===
        lbl_mode = vcl.TLabel(Form)
        lbl_mode.Parent = Form
        lbl_mode.Caption = "Fill with:"
        lbl_mode.Left = 20
        lbl_mode.Top = 140
        lbl_mode.Font.Style = {"fsBold"}
        labels.append(lbl_mode)
        
        # Panel container for fill mode radio buttons (invisible, for grouping)
        pnl_fill_mode = vcl.TPanel(Form)
        pnl_fill_mode.Parent = Form
        pnl_fill_mode.Left = 15
        pnl_fill_mode.Top = 160
        pnl_fill_mode.Width = 400
        pnl_fill_mode.Height = 110
        pnl_fill_mode.BevelOuter = "bvNone"
        
        rb_constant = vcl.TRadioButton(Form)
        rb_constant.Parent = pnl_fill_mode
        rb_constant.Caption = "Constant value"
        rb_constant.Left = 5
        rb_constant.Top = 5
        rb_constant.Width = 150
        rb_constant.Checked = True
        
        edt_constant = vcl.TEdit(Form)
        edt_constant.Parent = pnl_fill_mode
        edt_constant.Left = 155
        edt_constant.Top = 2
        edt_constant.Width = 100
        edt_constant.Text = "0.0"
        
        rb_from_series = vcl.TRadioButton(Form)
        rb_from_series.Parent = pnl_fill_mode
        rb_from_series.Caption = "Values from another series"
        rb_from_series.Left = 5
        rb_from_series.Top = 35
        rb_from_series.Width = 200
        rb_from_series.Checked = False
        
        rb_remove_rows = vcl.TRadioButton(Form)
        rb_remove_rows.Parent = pnl_fill_mode
        rb_remove_rows.Caption = "Remove rows (delete points in segment)"
        rb_remove_rows.Left = 5
        rb_remove_rows.Top = 95
        rb_remove_rows.Width = 300
        rb_remove_rows.Checked = False
        
        cb_source_series = vcl.TComboBox(Form)
        cb_source_series.Parent = pnl_fill_mode
        cb_source_series.Left = 25
        cb_source_series.Top = 60
        cb_source_series.Width = 350
        cb_source_series.Style = "csDropDownList"
        cb_source_series.Enabled = False
        
        # Populate source series dropdown
        for s in other_series:
            x_s, y_s = get_series_data_np(s)
            series_info = f"{s.LegendText or '(unnamed)'} [{len(x_s)} pts, X: {x_s.min():.3g} - {x_s.max():.3g}]"
            cb_source_series.Items.Add(series_info)
        
        if len(other_series) > 0:
            cb_source_series.ItemIndex = 0
        else:
            cb_source_series.Items.Add("(no other series available)")
            cb_source_series.ItemIndex = 0
            rb_from_series.Enabled = False
        
        # Source series info label
        lbl_source_info = vcl.TLabel(Form)
        lbl_source_info.Parent = pnl_fill_mode
        lbl_source_info.Caption = ""
        lbl_source_info.Left = 25
        lbl_source_info.Top = 85
        lbl_source_info.Font.Color = 0x808080
        labels.append(lbl_source_info)
        
        # Separador
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 285
        sep2.Width = 420
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        # === Output options ===
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output:"
        lbl_output.Left = 20
        lbl_output.Top = 300
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Panel container for output radio buttons (invisible, for grouping)
        pnl_output = vcl.TPanel(Form)
        pnl_output.Parent = Form
        pnl_output.Left = 95
        pnl_output.Top = 295
        pnl_output.Width = 340
        pnl_output.Height = 25
        pnl_output.BevelOuter = "bvNone"
        
        rb_replace_original = vcl.TRadioButton(Form)
        rb_replace_original.Parent = pnl_output
        rb_replace_original.Caption = "Replace points in original series"
        rb_replace_original.Left = 5
        rb_replace_original.Top = 5
        rb_replace_original.Width = 220
        rb_replace_original.Checked = True
        
        rb_create_new = vcl.TRadioButton(Form)
        rb_create_new.Parent = pnl_output
        rb_create_new.Caption = "Create new series"
        rb_create_new.Left = 225
        rb_create_new.Top = 5
        rb_create_new.Width = 120
        rb_create_new.Checked = False
        
        # New series color (only visible when creating new series)
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "New series color:"
        lbl_color.Left = 100
        lbl_color.Top = 328
        lbl_color.Visible = False
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 220
        cb_color.Top = 325
        cb_color.Width = 120
        cb_color.Selected = 0xFF00AA  # Magenta por defecto
        cb_color.Visible = False
        
        # Help panel
        pnl_help = vcl.TPanel(Form)
        pnl_help.Parent = Form
        pnl_help.Left = 20
        pnl_help.Top = 360
        pnl_help.Width = 400
        pnl_help.Height = 65
        pnl_help.BevelOuter = "bvLowered"
        pnl_help.Color = 0xFFF8F0
        
        help_text = (
            "• If source series has different sampling rate, linear interpolation is used\n"
            "• Points outside source series range keep their original values\n"
            "• 'Remove rows' deletes points in the segment from the series\n"
            "• 'Replace original' modifies the selected series directly"
        )
        
        lbl_help = vcl.TLabel(Form)
        lbl_help.Parent = pnl_help
        lbl_help.Caption = help_text
        lbl_help.Left = 10
        lbl_help.Top = 5
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Fill Segment"
        btn_ok.ModalResult = 1
        btn_ok.Default = True
        btn_ok.Left = 120
        btn_ok.Top = 440
        btn_ok.Width = 100
        btn_ok.Height = 28
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        btn_cancel.Left = 235
        btn_cancel.Top = 440
        btn_cancel.Width = 100
        btn_cancel.Height = 28
        
        # ========== Event handlers ==========
        def update_points_in_range(Sender):
            """Update the count of points that will be affected."""
            try:
                start_x = float(edt_start.Text)
                end_x = float(edt_end.Text)
                mask = (x_orig >= start_x) & (x_orig <= end_x)
                count = int(np.sum(mask))
                lbl_points_in_range.Caption = f"({count} points)"
            except:
                lbl_points_in_range.Caption = "(invalid)"
        
        def update_mode(Sender):
            """Enable/disable controls based on selected mode."""
            if rb_constant.Checked:
                edt_constant.Enabled = True
                cb_source_series.Enabled = False
                lbl_source_info.Caption = ""
            elif rb_from_series.Checked:
                edt_constant.Enabled = False
                cb_source_series.Enabled = len(other_series) > 0
                update_source_info(None)
            else:  # rb_remove_rows
                edt_constant.Enabled = False
                cb_source_series.Enabled = False
                lbl_source_info.Caption = ""
        
        def update_source_info(Sender):
            """Update source series info when selection changes."""
            if rb_from_series.Checked and len(other_series) > 0:
                idx = cb_source_series.ItemIndex
                if idx >= 0 and idx < len(other_series):
                    source = other_series[idx]
                    x_s, _ = get_series_data_np(source)
                    dx_s = np.diff(x_s)
                    period_s = float(np.mean(dx_s)) if len(dx_s) > 0 else 0
                    if abs(period_s - current_period) > current_period * 0.01:
                        lbl_source_info.Caption = f"Ts ≈ {period_s:.4g} (will interpolate to match)"
                        lbl_source_info.Font.Color = 0x0000AA
                    else:
                        lbl_source_info.Caption = f"Ts ≈ {period_s:.4g} (matching)"
                        lbl_source_info.Font.Color = 0x008800
        
        def update_output_mode(Sender):
            """Show/hide color selector based on output mode."""
            show_color = rb_create_new.Checked
            lbl_color.Visible = show_color
            cb_color.Visible = show_color
        
        # Assign event handlers
        edt_start.OnChange = update_points_in_range
        edt_end.OnChange = update_points_in_range
        rb_constant.OnClick = update_mode
        rb_from_series.OnClick = update_mode
        rb_remove_rows.OnClick = update_mode
        cb_source_series.OnChange = update_source_info
        rb_replace_original.OnClick = update_output_mode
        rb_create_new.OnClick = update_output_mode
        
        # Initial update
        update_points_in_range(None)
        update_output_mode(None)
        
        if Form.ShowModal() == 1:
            try:
                # Get parameters
                start_x = float(edt_start.Text)
                end_x = float(edt_end.Text)
                
                if start_x >= end_x:
                    raise ValueError("Start X must be less than End X")
                
                # Create mask for segment
                mask = (x_orig >= start_x) & (x_orig <= end_x)
                n_affected = int(np.sum(mask))
                
                if n_affected == 0:
                    raise ValueError("No points in the specified range")
                
                # Copy original data
                y_new = y_orig.copy()
                
                # Get X values in the segment
                x_segment = x_orig[mask]
                
                if rb_constant.Checked:
                    # Fill with constant value
                    constant_val = float(edt_constant.Text)
                    y_new[mask] = constant_val
                    fill_description = f"constant={constant_val}"
                    n_not_replaced = 0  # All points are replaced with constant
                elif rb_remove_rows.Checked:
                    # Remove rows mode - we'll handle this separately
                    fill_description = "rows removed"
                    n_not_replaced = 0
                    
                    # Filter out points in the segment
                    keep_mask = ~mask
                    x_new_filtered = x_orig[keep_mask]
                    y_new_filtered = y_orig[keep_mask]
                    
                    if len(x_new_filtered) == 0:
                        raise ValueError("Cannot remove all points from the series")
                    
                    # Apply changes based on output mode
                    if rb_replace_original.Checked:
                        new_points = [Point(float(x), float(y)) for x, y in zip(x_new_filtered, y_new_filtered)]
                        point_series.Points = new_points
                        Graph.Update()
                        output_mode_desc = "original series modified"
                    else:
                        color = int(cb_color.Selected) & 0xFFFFFF
                        new_points = [Point(float(x), float(y)) for x, y in zip(x_new_filtered, y_new_filtered)]
                        
                        new_series = Graph.TPointSeries()
                        new_series.PointType = Graph.ptCartesian
                        new_series.Points = new_points
                        new_series.LegendText = f"{point_series.LegendText} (cut [{start_x:.4g}, {end_x:.4g}])"
                        new_series.Size = 0
                        new_series.Style = 0
                        new_series.LineSize = 1
                        new_series.ShowLabels = False
                        
                        color_val = safe_color(color)
                        new_series.FillColor = color_val
                        new_series.FrameColor = color_val
                        new_series.LineColor = color_val
                        
                        Graph.FunctionList.append(new_series)
                        Graph.Update()
                        output_mode_desc = "new series created"
                    
                    # Show result message for remove mode
                    msg = (
                        f"Rows removed successfully.\n\n"
                        f"Range: [{start_x:.4g}, {end_x:.4g}]\n"
                        f"Points removed: {n_affected}\n"
                        f"Remaining points: {len(x_new_filtered)}\n"
                        f"Output: {output_mode_desc}"
                    )
                    show_info(msg, "Fill Segment")
                    return  # Exit early since we handled everything
                else:
                    # Fill with values from another series
                    if len(other_series) == 0:
                        raise ValueError("No other series available")
                    
                    idx = cb_source_series.ItemIndex
                    if idx < 0 or idx >= len(other_series):
                        raise ValueError("Invalid source series selection")
                    
                    source_series = other_series[idx]
                    x_source, y_source = get_series_data_np(source_series)
                    
                    # Interpolate source values at segment X positions
                    y_interpolated = interpolate_series_values(x_segment, x_source, y_source)
                    
                    # Count points that couldn't be interpolated (outside source range)
                    nan_mask = np.isnan(y_interpolated)
                    n_not_replaced = int(np.sum(nan_mask))
                    
                    # Only replace values where interpolation was successful
                    # Keep original values where interpolation returned NaN
                    segment_indices = np.where(mask)[0]
                    for i, idx in enumerate(segment_indices):
                        if not np.isnan(y_interpolated[i]):
                            y_new[idx] = y_interpolated[i]
                        # else: keep original value (y_new[idx] already has it)
                    
                    fill_description = f"from '{source_series.LegendText or 'unnamed'}'"
                
                # Apply changes based on output mode
                if rb_replace_original.Checked:
                    # Replace points in original series
                    new_points = [Point(float(x), float(y)) for x, y in zip(x_orig, y_new)]
                    point_series.Points = new_points
                    Graph.Update()
                    output_mode_desc = "original series modified"
                else:
                    # Create new series
                    color = int(cb_color.Selected) & 0xFFFFFF
                    new_points = [Point(float(x), float(y)) for x, y in zip(x_orig, y_new)]
                    
                    new_series = Graph.TPointSeries()
                    new_series.PointType = Graph.ptCartesian
                    new_series.Points = new_points
                    new_series.LegendText = f"{point_series.LegendText} (filled [{start_x:.4g}, {end_x:.4g}])"
                    new_series.Size = 0
                    new_series.Style = 0
                    new_series.LineSize = 1
                    new_series.ShowLabels = False
                    
                    color_val = safe_color(color)
                    new_series.FillColor = color_val
                    new_series.FrameColor = color_val
                    new_series.LineColor = color_val
                    
                    Graph.FunctionList.append(new_series)
                    Graph.Update()
                    output_mode_desc = "new series created"
                
                # Build result message
                msg = (
                    f"Segment filled successfully.\n\n"
                    f"Range: [{start_x:.4g}, {end_x:.4g}]\n"
                    f"Points affected: {n_affected}\n"
                    f"Fill mode: {fill_description}\n"
                    f"Output: {output_mode_desc}"
                )
                
                # Add warning if some points weren't replaced (only for series fill mode)
                if not rb_constant.Checked and n_not_replaced > 0:
                    msg += f"\n\n⚠ {n_not_replaced} points were NOT replaced\n(source series doesn't cover those X values)"
                
                show_info(msg, "Fill Segment")
                
            except Exception as e:
                show_error(f"Error filling segment: {str(e)}", "Fill Segment")
    
    finally:
        Form.Free()


# Create action for menu
FillSegmentAction = Graph.CreateAction(
    Caption="Fill Segment...",
    OnExecute=fill_segment,
    Hint="Fills a segment of the selected series with constant values or values from another series.",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "FillSegment_sm.png")
)

# Add action to Plugins menu
Graph.AddActionToMainMenu(FillSegmentAction, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"])  # type: ignore
