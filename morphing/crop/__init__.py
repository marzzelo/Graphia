"""
Crop/Cut - Plugin to crop or cut data based on a selected area
Allows drawing rectangles and performing area-based data operations.
"""

import Graph
import vcl
import os
from collections import namedtuple

# Import common utilities
from common import (
    get_selected_point_series, show_error, show_info, get_series_data, 
    Point, safe_color
)

PluginName = "Crop/Cut"
PluginVersion = "1.3"
PluginDescription = "Draw rectangles or crop/cut data based on selected area."


def CropCutDialog(Action):
    """
    Opens a dialog to configure area selection and perform operations.
    """
    # Get selected series (optional - for info labels)
    series, _ = get_selected_point_series()
    
    # Get series data if available
    series_x_min = series_x_max = series_y_min = series_y_max = None
    x_vals = y_vals = None
    if series:
        x_vals, y_vals = get_series_data(series)
        if x_vals and y_vals:
            series_x_min = min(x_vals)
            series_x_max = max(x_vals)
            series_y_min = min(y_vals)
            series_y_max = max(y_vals)
    
    # Get current axis limits (defaults)
    x_min_default = Graph.Axes.xAxis.Min
    x_max_default = Graph.Axes.xAxis.Max
    y_min_default = Graph.Axes.yAxis.Min
    y_max_default = Graph.Axes.yAxis.Max
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Crop / Cut"
        Form.Width = 500
        Form.Height = 560
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []  # Keep references
        
        # =====================================================================
        # Select Area Section
        # =====================================================================
        lbl_area = vcl.TLabel(Form)
        lbl_area.Parent = Form
        lbl_area.Caption = "Select Area"
        lbl_area.Left = 10
        lbl_area.Top = 10
        lbl_area.Font.Style = {"fsBold"}
        labels.append(lbl_area)
        
        # Panel for area inputs
        pnl_area = vcl.TPanel(Form)
        pnl_area.Parent = Form
        pnl_area.Left = 10
        pnl_area.Top = 35
        pnl_area.Width = 470
        pnl_area.Height = 165
        pnl_area.BevelOuter = "bvLowered"
        
        # Build list of rectangle series
        rect_series_list = []  # List of (name, series) tuples
        for item in Graph.FunctionList:
            if hasattr(item, 'LegendText') and item.LegendText and 'Rect' in item.LegendText:
                rect_series_list.append((item.LegendText, item))
        
        # Area source selector
        lbl_source = vcl.TLabel(Form)
        lbl_source.Parent = pnl_area
        lbl_source.Caption = "Source:"
        lbl_source.Left = 15
        lbl_source.Top = 15
        labels.append(lbl_source)
        
        cmb_source = vcl.TComboBox(Form)
        cmb_source.Parent = pnl_area
        cmb_source.Left = 80
        cmb_source.Top = 12
        cmb_source.Width = 370
        cmb_source.Style = 2  # csDropDownList - read only
        cmb_source.Items.Add("Visible Area")
        for name, _ in rect_series_list:
            cmb_source.Items.Add(name)
        cmb_source.ItemIndex = 0
        
        # Function to update coordinates from selected source
        def on_source_change(Sender):
            idx = cmb_source.ItemIndex
            if idx == 0:
                # Visible Area
                edt_xleft.Text = f"{x_min_default:.6g}"
                edt_xright.Text = f"{x_max_default:.6g}"
                edt_ybottom.Text = f"{y_min_default:.6g}"
                edt_ytop.Text = f"{y_max_default:.6g}"
            elif idx > 0 and idx <= len(rect_series_list):
                # Rectangle series
                _, rect_series = rect_series_list[idx - 1]
                rx_vals, ry_vals = get_series_data(rect_series)
                if rx_vals and ry_vals:
                    edt_xleft.Text = f"{min(rx_vals):.6g}"
                    edt_xright.Text = f"{max(rx_vals):.6g}"
                    edt_ybottom.Text = f"{min(ry_vals):.6g}"
                    edt_ytop.Text = f"{max(ry_vals):.6g}"
        
        cmb_source.OnChange = on_source_change
        
        # X Left
        lbl_xleft = vcl.TLabel(Form)
        lbl_xleft.Parent = pnl_area
        lbl_xleft.Caption = "X Left:"
        lbl_xleft.Left = 15
        lbl_xleft.Top = 48
        labels.append(lbl_xleft)
        
        edt_xleft = vcl.TEdit(Form)
        edt_xleft.Parent = pnl_area
        edt_xleft.Left = 80
        edt_xleft.Top = 45
        edt_xleft.Width = 120
        edt_xleft.Text = f"{x_min_default:.6g}"
        
        lbl_xleft_info = vcl.TLabel(Form)
        lbl_xleft_info.Parent = pnl_area
        lbl_xleft_info.Caption = f"xmin: {series_x_min:.4g}" if series_x_min is not None else "xmin: N/A"
        lbl_xleft_info.Left = 210
        lbl_xleft_info.Top = 48
        lbl_xleft_info.Font.Color = 0x666666
        labels.append(lbl_xleft_info)
        
        # X Right
        lbl_xright = vcl.TLabel(Form)
        lbl_xright.Parent = pnl_area
        lbl_xright.Caption = "X Right:"
        lbl_xright.Left = 15
        lbl_xright.Top = 76
        labels.append(lbl_xright)
        
        edt_xright = vcl.TEdit(Form)
        edt_xright.Parent = pnl_area
        edt_xright.Left = 80
        edt_xright.Top = 73
        edt_xright.Width = 120
        edt_xright.Text = f"{x_max_default:.6g}"
        
        lbl_xright_info = vcl.TLabel(Form)
        lbl_xright_info.Parent = pnl_area
        lbl_xright_info.Caption = f"xmax: {series_x_max:.4g}" if series_x_max is not None else "xmax: N/A"
        lbl_xright_info.Left = 210
        lbl_xright_info.Top = 76
        lbl_xright_info.Font.Color = 0x666666
        labels.append(lbl_xright_info)
        
        # Y Bottom
        lbl_ybottom = vcl.TLabel(Form)
        lbl_ybottom.Parent = pnl_area
        lbl_ybottom.Caption = "Y Bottom:"
        lbl_ybottom.Left = 15
        lbl_ybottom.Top = 104
        labels.append(lbl_ybottom)
        
        edt_ybottom = vcl.TEdit(Form)
        edt_ybottom.Parent = pnl_area
        edt_ybottom.Left = 80
        edt_ybottom.Top = 101
        edt_ybottom.Width = 120
        edt_ybottom.Text = f"{y_min_default:.6g}"
        
        lbl_ybottom_info = vcl.TLabel(Form)
        lbl_ybottom_info.Parent = pnl_area
        lbl_ybottom_info.Caption = f"ymin: {series_y_min:.4g}" if series_y_min is not None else "ymin: N/A"
        lbl_ybottom_info.Left = 210
        lbl_ybottom_info.Top = 104
        lbl_ybottom_info.Font.Color = 0x666666
        labels.append(lbl_ybottom_info)
        
        # Y Top
        lbl_ytop = vcl.TLabel(Form)
        lbl_ytop.Parent = pnl_area
        lbl_ytop.Caption = "Y Top:"
        lbl_ytop.Left = 15
        lbl_ytop.Top = 132
        labels.append(lbl_ytop)
        
        edt_ytop = vcl.TEdit(Form)
        edt_ytop.Parent = pnl_area
        edt_ytop.Left = 80
        edt_ytop.Top = 129
        edt_ytop.Width = 120
        edt_ytop.Text = f"{y_max_default:.6g}"
        
        lbl_ytop_info = vcl.TLabel(Form)
        lbl_ytop_info.Parent = pnl_area
        lbl_ytop_info.Caption = f"ymax: {series_y_max:.4g}" if series_y_max is not None else "ymax: N/A"
        lbl_ytop_info.Left = 210
        lbl_ytop_info.Top = 132
        lbl_ytop_info.Font.Color = 0x666666
        labels.append(lbl_ytop_info)
        
        # =====================================================================
        # Mode Section
        # =====================================================================
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 210
        sep1.Width = 470
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        lbl_mode = vcl.TLabel(Form)
        lbl_mode.Parent = Form
        lbl_mode.Caption = "Output Mode"
        lbl_mode.Left = 10
        lbl_mode.Top = 220
        lbl_mode.Font.Style = {"fsBold"}
        labels.append(lbl_mode)
        
        # Panel for mode options
        pnl_mode = vcl.TPanel(Form)
        pnl_mode.Parent = Form
        pnl_mode.Left = 10
        pnl_mode.Top = 243
        pnl_mode.Width = 470
        pnl_mode.Height = 60
        pnl_mode.BevelOuter = "bvNone"
        
        rb_new = vcl.TRadioButton(Form)
        rb_new.Parent = pnl_mode
        rb_new.Caption = "Create new series"
        rb_new.Left = 10
        rb_new.Top = 5
        rb_new.Checked = True
        
        rb_replace = vcl.TRadioButton(Form)
        rb_replace.Parent = pnl_mode
        rb_replace.Caption = "Replace original series"
        rb_replace.Left = 200
        rb_replace.Top = 5
        
        # Color selector
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = pnl_mode
        lbl_color.Caption = "New Series Color:"
        lbl_color.Left = 10
        lbl_color.Top = 35
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = pnl_mode
        cb_color.Left = 130
        cb_color.Top = 32
        cb_color.Width = 100
        cb_color.Selected = 0x00AA00  # Green by default
        
        # =====================================================================
        # Actions Section
        # =====================================================================
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 313
        sep2.Width = 470
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        lbl_actions = vcl.TLabel(Form)
        lbl_actions.Parent = Form
        lbl_actions.Caption = "Actions"
        lbl_actions.Left = 10
        lbl_actions.Top = 323
        lbl_actions.Font.Style = {"fsBold"}
        labels.append(lbl_actions)
        
        # Panel for action buttons
        pnl_actions = vcl.TPanel(Form)
        pnl_actions.Parent = Form
        pnl_actions.Left = 10
        pnl_actions.Top = 345
        pnl_actions.Width = 470
        pnl_actions.Height = 120
        pnl_actions.BevelOuter = "bvLowered"
        
        # Helper function to get area values
        def get_area_values():
            try:
                xleft = float(edt_xleft.Text)
                xright = float(edt_xright.Text)
                ybottom = float(edt_ybottom.Text)
                ytop = float(edt_ytop.Text)
                return xleft, xright, ybottom, ytop
            except ValueError as e:
                show_error("Invalid numeric value in area fields.", "Crop/Cut")
                return None
        
        # Helper to create/update series
        def apply_filtered_points(new_points, operation_name):
            nonlocal series
            if not new_points:
                show_error(f"No points remaining after {operation_name}.", "Crop/Cut")
                return False
            
            if rb_new.Checked:
                new_series = Graph.TPointSeries()
                if series:
                    new_series.PointType = series.PointType
                    new_series.Size = series.Size
                    new_series.Style = series.Style
                    new_series.LineSize = series.LineSize
                    new_series.ShowLabels = series.ShowLabels
                    original_legend = series.LegendText if series.LegendText else "Series"
                    new_series.LegendText = f"{original_legend} [{operation_name}]"
                else:
                    new_series.LegendText = operation_name
                    new_series.Size = 0
                    new_series.LineSize = 1
                    new_series.ShowLabels = False
                
                new_series.Points = new_points
                color_val = safe_color(cb_color.Selected)
                new_series.FillColor = color_val
                new_series.FrameColor = color_val
                new_series.LineColor = color_val
                
                Graph.FunctionList.append(new_series)
            else:
                if series:
                    series.Points = new_points
                    if series.LegendText:
                        series.LegendText = f"{series.LegendText} [{operation_name}]"
                else:
                    show_error("No series selected to replace.", "Crop/Cut")
                    return False
            
            Graph.Update()
            show_info(f"{operation_name} completed. {len(new_points)} points.", "Crop/Cut")
            return True
        
        # Crop X - keep points inside X range
        def on_crop_x(Sender):
            if not series or not x_vals:
                show_error("No series selected.", "Crop/Cut")
                return
            area = get_area_values()
            if not area:
                return
            xleft, xright, _, _ = area
            new_points = [Point(x, y) for x, y in zip(x_vals, y_vals) 
                          if xleft <= x <= xright]
            apply_filtered_points(new_points, "Crop X")
        
        # Crop Y - keep points inside Y range
        def on_crop_y(Sender):
            if not series or not y_vals:
                show_error("No series selected.", "Crop/Cut")
                return
            area = get_area_values()
            if not area:
                return
            _, _, ybottom, ytop = area
            new_points = [Point(x, y) for x, y in zip(x_vals, y_vals) 
                          if ybottom <= y <= ytop]
            apply_filtered_points(new_points, "Crop Y")
        
        # Cut X - remove points inside X range
        def on_cut_x(Sender):
            if not series or not x_vals:
                show_error("No series selected.", "Crop/Cut")
                return
            area = get_area_values()
            if not area:
                return
            xleft, xright, _, _ = area
            new_points = [Point(x, y) for x, y in zip(x_vals, y_vals) 
                          if x < xleft or x > xright]
            apply_filtered_points(new_points, "Cut X")
        
        # Cut Y - remove points inside Y range
        def on_cut_y(Sender):
            if not series or not y_vals:
                show_error("No series selected.", "Crop/Cut")
                return
            area = get_area_values()
            if not area:
                return
            _, _, ybottom, ytop = area
            new_points = [Point(x, y) for x, y in zip(x_vals, y_vals) 
                          if y < ybottom or y > ytop]
            apply_filtered_points(new_points, "Cut Y")
        
        # Crop XY - keep points inside both X and Y range
        def on_crop_xy(Sender):
            if not series or not x_vals:
                show_error("No series selected.", "Crop/Cut")
                return
            area = get_area_values()
            if not area:
                return
            xleft, xright, ybottom, ytop = area
            new_points = [Point(x, y) for x, y in zip(x_vals, y_vals) 
                          if xleft <= x <= xright and ybottom <= y <= ytop]
            apply_filtered_points(new_points, "Crop XY")
        
        # Cut XY - remove points inside both X and Y range
        def on_cut_xy(Sender):
            if not series or not x_vals:
                show_error("No series selected.", "Crop/Cut")
                return
            area = get_area_values()
            if not area:
                return
            xleft, xright, ybottom, ytop = area
            new_points = [Point(x, y) for x, y in zip(x_vals, y_vals) 
                          if not (xleft <= x <= xright and ybottom <= y <= ytop)]
            apply_filtered_points(new_points, "Cut XY")
        
        # Draw Rectangle
        def on_draw_rect(Sender):
            area = get_area_values()
            if not area:
                return
            xleft, xright, ybottom, ytop = area
            
            # Define the 5 rectangle points (close the loop)
            rect_points = [
                Point(xleft, ybottom),
                Point(xright, ybottom),
                Point(xright, ytop),
                Point(xleft, ytop),
                Point(xleft, ybottom)
            ]
            
            # Create point series
            rect_series = Graph.TPointSeries()
            rect_series.Points = rect_points
            rect_series.LegendText = f"Rect [{xleft:.3g}, {xright:.3g}] x [{ybottom:.3g}, {ytop:.3g}]"
            
            # Configure style
            rect_series.Size = 0          # No markers
            rect_series.Style = 0         # Marker style
            rect_series.LineSize = 2      # Line width
            
            # Use selected color
            color_val = safe_color(cb_color.Selected)
            rect_series.LineColor = color_val
            rect_series.FillColor = color_val
            rect_series.FrameColor = color_val
            
            rect_series.LineStyle = 2  # 2 is dotted line          
            rect_series.ShowLabels = False
            
            Graph.FunctionList.append(rect_series)
            Graph.Update()
            show_info("Rectangle drawn.", "Crop/Cut")
        
        # Action buttons
        btn_crop_x = vcl.TButton(Form)
        btn_crop_x.Parent = pnl_actions
        btn_crop_x.Caption = "Crop X"
        btn_crop_x.Left = 15
        btn_crop_x.Top = 15
        btn_crop_x.Width = 100
        btn_crop_x.Height = 28
        btn_crop_x.OnClick = on_crop_x
        btn_crop_x.Hint = "Keep points inside X range"
        btn_crop_x.ShowHint = True
        
        btn_crop_y = vcl.TButton(Form)
        btn_crop_y.Parent = pnl_actions
        btn_crop_y.Caption = "Crop Y"
        btn_crop_y.Left = 125
        btn_crop_y.Top = 15
        btn_crop_y.Width = 100
        btn_crop_y.Height = 28
        btn_crop_y.OnClick = on_crop_y
        btn_crop_y.Hint = "Keep points inside Y range"
        btn_crop_y.ShowHint = True
        
        btn_cut_x = vcl.TButton(Form)
        btn_cut_x.Parent = pnl_actions
        btn_cut_x.Caption = "Cut X"
        btn_cut_x.Left = 15
        btn_cut_x.Top = 50
        btn_cut_x.Width = 100
        btn_cut_x.Height = 28
        btn_cut_x.OnClick = on_cut_x
        btn_cut_x.Hint = "Remove points inside X range"
        btn_cut_x.ShowHint = True
        
        btn_cut_y = vcl.TButton(Form)
        btn_cut_y.Parent = pnl_actions
        btn_cut_y.Caption = "Cut Y"
        btn_cut_y.Left = 125
        btn_cut_y.Top = 50
        btn_cut_y.Width = 100
        btn_cut_y.Height = 28
        btn_cut_y.OnClick = on_cut_y
        btn_cut_y.Hint = "Remove points inside Y range"
        btn_cut_y.ShowHint = True
        
        btn_crop_xy = vcl.TButton(Form)
        btn_crop_xy.Parent = pnl_actions
        btn_crop_xy.Caption = "Crop XY"
        btn_crop_xy.Left = 245
        btn_crop_xy.Top = 15
        btn_crop_xy.Width = 100
        btn_crop_xy.Height = 28
        btn_crop_xy.OnClick = on_crop_xy
        btn_crop_xy.Hint = "Keep points inside XY area"
        btn_crop_xy.ShowHint = True
        
        btn_cut_xy = vcl.TButton(Form)
        btn_cut_xy.Parent = pnl_actions
        btn_cut_xy.Caption = "Cut XY"
        btn_cut_xy.Left = 245
        btn_cut_xy.Top = 50
        btn_cut_xy.Width = 100
        btn_cut_xy.Height = 28
        btn_cut_xy.OnClick = on_cut_xy
        btn_cut_xy.Hint = "Remove points inside XY area"
        btn_cut_xy.ShowHint = True
        
        btn_draw_rect = vcl.TButton(Form)
        btn_draw_rect.Parent = pnl_actions
        btn_draw_rect.Caption = "Draw Rectangle"
        btn_draw_rect.Left = 15
        btn_draw_rect.Top = 85
        btn_draw_rect.Width = 330
        btn_draw_rect.Height = 28
        btn_draw_rect.OnClick = on_draw_rect
        btn_draw_rect.Hint = "Draw a rectangle around the selected area"
        btn_draw_rect.ShowHint = True
        
        # =====================================================================
        # OK/Cancel Buttons
        # =====================================================================
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 475
        sep3.Width = 470
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "OK"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 290
        btn_ok.Top = 490
        btn_ok.Width = 90
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 390
        btn_cancel.Top = 490
        btn_cancel.Width = 90
        btn_cancel.Height = 30
        
        # Show dialog
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="Crop/Cut...",
    OnExecute=CropCutDialog,
    Hint="Crop or cut data based on selected area",
    IconFile=os.path.join(os.path.dirname(__file__), "Crop_sm.png")
)

# Add to Plugins -> Morphing menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"]) # type: ignore
