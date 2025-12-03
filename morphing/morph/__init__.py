"""
Morph - Plugin to transform point series to new limits
Allows scaling and shifting a series so that its X and Y values
fall within the new limits specified by the user.
"""

import Graph
import vcl # type: ignore
import os

# Import common utilities
from common import setup_venv, get_selected_point_series, show_error, show_info, get_series_data, Point, safe_color

# Import numpy
import numpy as np


def morph_series(Action):
    """
    Shows a dialog to transform the selected series to new limits.
    """
    # Get selected series
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "Morph")
        return

    # Get current data
    x_vals, y_vals = get_series_data(series)
    
    if not y_vals:
        show_info("The selected series has no points.", "Morph")
        return

    # Calculate current limits
    x_arr = np.array(x_vals)
    y_arr = np.array(y_vals)
    
    current_xmin = float(np.min(x_arr))
    current_xmax = float(np.max(x_arr))
    current_ymin = float(np.min(y_arr))
    current_ymax = float(np.max(y_arr))
    
    # Get visible area limits (defaults for new limits)
    visible_xmin = Graph.Axes.xAxis.Min
    visible_xmax = Graph.Axes.xAxis.Max
    visible_ymin = Graph.Axes.yAxis.Min
    visible_ymax = Graph.Axes.yAxis.Max

    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Morph - Transform Series"
        Form.Width = 380
        Form.Height = 380
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []  # Keep references
        
        # Title
        lbl_title = vcl.TLabel(Form)
        lbl_title.Parent = Form
        lbl_title.Caption = "Define new limits for the series"
        lbl_title.Left = 20
        lbl_title.Top = 15
        lbl_title.Font.Style = {"fsBold"}
        labels.append(lbl_title)
        
        # Series name
        if series.LegendText:
            lbl_series = vcl.TLabel(Form)
            lbl_series.Parent = Form
            lbl_series.Caption = f"Series: {series.LegendText}"
            lbl_series.Left = 20
            lbl_series.Top = 35
            lbl_series.Font.Color = 0x666666
            labels.append(lbl_series)
        
        # Frame for fields
        y_top = 60
        
        # Xmin
        lbl_xmin = vcl.TLabel(Form)
        lbl_xmin.Parent = Form
        lbl_xmin.Caption = "Xmin:"
        lbl_xmin.Left = 20
        lbl_xmin.Top = y_top + 5
        labels.append(lbl_xmin)
        
        edt_xmin = vcl.TEdit(Form)
        edt_xmin.Parent = Form
        edt_xmin.Left = 100
        edt_xmin.Top = y_top
        edt_xmin.Width = 120
        edt_xmin.Text = f"{visible_xmin:.6g}"
        
        lbl_xmin_cur = vcl.TLabel(Form)
        lbl_xmin_cur.Parent = Form
        lbl_xmin_cur.Caption = f"(current: {current_xmin:.4g})"
        lbl_xmin_cur.Left = 230
        lbl_xmin_cur.Top = y_top + 5
        lbl_xmin_cur.Font.Color = 0x888888
        labels.append(lbl_xmin_cur)
        
        # Xmax
        y_top += 30
        lbl_xmax = vcl.TLabel(Form)
        lbl_xmax.Parent = Form
        lbl_xmax.Caption = "Xmax:"
        lbl_xmax.Left = 20
        lbl_xmax.Top = y_top + 5
        labels.append(lbl_xmax)
        
        edt_xmax = vcl.TEdit(Form)
        edt_xmax.Parent = Form
        edt_xmax.Left = 100
        edt_xmax.Top = y_top
        edt_xmax.Width = 120
        edt_xmax.Text = f"{visible_xmax:.6g}"
        
        lbl_xmax_cur = vcl.TLabel(Form)
        lbl_xmax_cur.Parent = Form
        lbl_xmax_cur.Caption = f"(current: {current_xmax:.4g})"
        lbl_xmax_cur.Left = 230
        lbl_xmax_cur.Top = y_top + 5
        lbl_xmax_cur.Font.Color = 0x888888
        labels.append(lbl_xmax_cur)
        
        # Ymin
        y_top += 40
        lbl_ymin = vcl.TLabel(Form)
        lbl_ymin.Parent = Form
        lbl_ymin.Caption = "Ymin:"
        lbl_ymin.Left = 20
        lbl_ymin.Top = y_top + 5
        labels.append(lbl_ymin)
        
        edt_ymin = vcl.TEdit(Form)
        edt_ymin.Parent = Form
        edt_ymin.Left = 100
        edt_ymin.Top = y_top
        edt_ymin.Width = 120
        edt_ymin.Text = f"{visible_ymin:.6g}"
        
        lbl_ymin_cur = vcl.TLabel(Form)
        lbl_ymin_cur.Parent = Form
        lbl_ymin_cur.Caption = f"(current: {current_ymin:.4g})"
        lbl_ymin_cur.Left = 230
        lbl_ymin_cur.Top = y_top + 5
        lbl_ymin_cur.Font.Color = 0x888888
        labels.append(lbl_ymin_cur)
        
        # Ymax
        y_top += 30
        lbl_ymax = vcl.TLabel(Form)
        lbl_ymax.Parent = Form
        lbl_ymax.Caption = "Ymax:"
        lbl_ymax.Left = 20
        lbl_ymax.Top = y_top + 5
        labels.append(lbl_ymax)
        
        edt_ymax = vcl.TEdit(Form)
        edt_ymax.Parent = Form
        edt_ymax.Left = 100
        edt_ymax.Top = y_top
        edt_ymax.Width = 120
        edt_ymax.Text = f"{visible_ymax:.6g}"
        
        lbl_ymax_cur = vcl.TLabel(Form)
        lbl_ymax_cur.Parent = Form
        lbl_ymax_cur.Caption = f"(current: {current_ymax:.4g})"
        lbl_ymax_cur.Left = 230
        lbl_ymax_cur.Top = y_top + 5
        lbl_ymax_cur.Font.Color = 0x888888
        labels.append(lbl_ymax_cur)
        
        # Separator
        y_top += 40
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = y_top
        sep1.Width = 350
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Output section
        y_top += 10
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output"
        lbl_output.Left = 20
        lbl_output.Top = y_top
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Panel to group output radio buttons
        y_top += 20
        pnl_output = vcl.TPanel(Form)
        pnl_output.Parent = Form
        pnl_output.Left = 10
        pnl_output.Top = y_top
        pnl_output.Width = 350
        pnl_output.Height = 30
        pnl_output.BevelOuter = "bvNone"
        
        rb_new = vcl.TRadioButton(Form)
        rb_new.Parent = pnl_output
        rb_new.Caption = "Create new series"
        rb_new.Left = 10
        rb_new.Top = 5
        rb_new.Checked = True
        
        rb_replace = vcl.TRadioButton(Form)
        rb_replace.Parent = pnl_output
        rb_replace.Caption = "Replace original series"
        rb_replace.Left = 180
        rb_replace.Top = 5
        
        # Color for new series
        y_top += 35
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Color (new series):"
        lbl_color.Left = 20
        lbl_color.Top = y_top + 3
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 140
        cb_color.Top = y_top
        cb_color.Width = 100
        cb_color.Selected = 0x00AA00  # Green by default
        
        # Buttons
        y_top += 45
        
        btn_morph = vcl.TButton(Form)
        btn_morph.Parent = Form
        btn_morph.Caption = "Morph!"
        btn_morph.Left = 100
        btn_morph.Top = y_top
        btn_morph.Width = 80
        btn_morph.Height = 30
        
        btn_close = vcl.TButton(Form)
        btn_close.Parent = Form
        btn_close.Caption = "Close"
        btn_close.ModalResult = 2
        btn_close.Cancel = True
        btn_close.Left = 200
        btn_close.Top = y_top
        btn_close.Width = 80
        btn_close.Height = 30
        
        def on_morph_click(Sender):
            try:
                new_xmin = float(edt_xmin.Text)
                new_xmax = float(edt_xmax.Text)
                new_ymin = float(edt_ymin.Text)
                new_ymax = float(edt_ymax.Text)
            except ValueError:
                show_error("Please enter valid numeric values.", "Morph")
                return
            
            # Validate ranges
            if new_xmax <= new_xmin:
                show_error("Xmax must be greater than Xmin.", "Morph")
                return
            if new_ymax <= new_ymin:
                show_error("Ymax must be greater than Ymin.", "Morph")
                return
            
            # Verify that current ranges are not zero
            x_range = current_xmax - current_xmin
            y_range = current_ymax - current_ymin
            
            if x_range == 0:
                show_error("Current X range is zero. Cannot scale.", "Morph")
                return
            if y_range == 0:
                show_error("Current Y range is zero. Cannot scale.", "Morph")
                return
            
            # Calculate scale factors
            # new_val = k * old_val + offset
            # So that old_min -> new_min and old_max -> new_max:
            # k = (new_max - new_min) / (old_max - old_min)
            # offset = new_min - k * old_min
            
            kx = (new_xmax - new_xmin) / x_range
            offset_x = new_xmin - kx * current_xmin
            
            ky = (new_ymax - new_ymin) / y_range
            offset_y = new_ymin - ky * current_ymin
            
            # Transform all points
            new_points = []
            for p in series.Points:
                new_x = kx * p.x + offset_x
                new_y = ky * p.y + offset_y
                new_points.append(Point(new_x, new_y))
            
            if rb_new.Checked:
                # Create new series
                new_series = Graph.TPointSeries()
                new_series.PointType = series.PointType
                new_series.Points = new_points
                
                # Copy display properties
                original_legend = series.LegendText
                new_series.LegendText = f"{original_legend} [morphed]"
                new_series.Size = series.Size
                new_series.Style = series.Style
                new_series.LineSize = series.LineSize
                new_series.ShowLabels = series.ShowLabels
                
                # Use selected color
                color_val = safe_color(cb_color.Selected)
                new_series.FillColor = color_val
                new_series.FrameColor = color_val
                new_series.LineColor = color_val
                
                Graph.FunctionList.append(new_series)
            else:
                # Replace points in original series
                series.Points = new_points
            
            Graph.Redraw()
        
        btn_morph.OnClick = on_morph_click
        
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="Morph...", 
    OnExecute=morph_series, 
    Hint="Transform the selected series to new X and Y limits",
    IconFile=os.path.join(os.path.dirname(__file__), "Morph_sm.png")
)

# Add to Plugins -> Morphing menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"]) # type: ignore
