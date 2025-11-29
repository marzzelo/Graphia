# Plugin to combine point series linearly
import os

# Import common module
from common import (
    get_selected_point_series, show_error, show_info, 
    safe_color, Point, Graph, vcl
)

import numpy as np
from scipy.interpolate import CubicSpline

PluginName = "Linear Combination"
PluginVersion = "1.0"
PluginDescription = "Combines point series linearly: y = Σ kᵢ·yᵢ"


def get_all_point_series():
    """Returns a list of all visible TPointSeries in the graph."""
    series_list = []
    for item in Graph.FunctionList:
        if type(item).__name__ == "TPointSeries" and item.Visible:
            series_list.append(item)
    return series_list


def linear_combination(Action):
    """Opens dialog to combine point series linearly."""
    
    # Get selected series (base series)
    base_series, error_msg = get_selected_point_series()
    if base_series is None:
        show_error(error_msg or "You must select a point series (TPointSeries) as base.", 
                   "Linear Combination")
        return
    
    # Get all visible point series
    all_series = get_all_point_series()
    if len(all_series) < 1:
        show_error("No visible point series found.", "Linear Combination")
        return
    
    # Get base series X values
    base_points = base_series.Points
    if len(base_points) < 2:
        show_error("Base series must have at least 2 points.", "Linear Combination")
        return
    
    x_base = np.array([p.x for p in base_points])
    
    # Calculate form height based on number of series
    row_height = 30
    header_height = 120
    footer_height = 120
    max_visible_rows = 10
    visible_rows = min(len(all_series), max_visible_rows)
    content_height = visible_rows * row_height + 10
    form_height = header_height + content_height + footer_height
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Linear Combination of Series"
        Form.Width = 500
        Form.Height = form_height
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []
        
        # Header info
        lbl_title = vcl.TLabel(Form)
        lbl_title.Parent = Form
        lbl_title.Caption = "Combine series: y = Σ kᵢ · yᵢ(x)"
        lbl_title.Left = 20
        lbl_title.Top = 15
        lbl_title.Font.Style = {"fsBold"}
        lbl_title.Font.Size = 10
        labels.append(lbl_title)
        
        lbl_base = vcl.TLabel(Form)
        lbl_base.Parent = Form
        base_legend = base_series.LegendText[:40] if len(base_series.LegendText) > 40 else base_series.LegendText
        lbl_base.Caption = f"Base series (X domain): {base_legend}"
        lbl_base.Left = 20
        lbl_base.Top = 40
        lbl_base.Font.Color = 0x666666
        labels.append(lbl_base)
        
        # Separator
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 65
        sep1.Width = 470
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Column headers
        lbl_col_sel = vcl.TLabel(Form)
        lbl_col_sel.Parent = Form
        lbl_col_sel.Caption = "Use"
        lbl_col_sel.Left = 25
        lbl_col_sel.Top = 75
        lbl_col_sel.Font.Style = {"fsBold"}
        labels.append(lbl_col_sel)
        
        lbl_col_factor = vcl.TLabel(Form)
        lbl_col_factor.Parent = Form
        lbl_col_factor.Caption = "Factor (kᵢ)"
        lbl_col_factor.Left = 70
        lbl_col_factor.Top = 75
        lbl_col_factor.Font.Style = {"fsBold"}
        labels.append(lbl_col_factor)
        
        lbl_col_series = vcl.TLabel(Form)
        lbl_col_series.Parent = Form
        lbl_col_series.Caption = "Series"
        lbl_col_series.Left = 170
        lbl_col_series.Top = 75
        lbl_col_series.Font.Style = {"fsBold"}
        labels.append(lbl_col_series)
        
        # Separator under headers
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 95
        sep2.Width = 470
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        # Scrollable area for series
        scroll_box = vcl.TScrollBox(Form)
        scroll_box.Parent = Form
        scroll_box.Left = 10
        scroll_box.Top = 100
        scroll_box.Width = 465
        scroll_box.Height = content_height
        scroll_box.BorderStyle = "bsNone"
        
        # Store controls for each series
        series_controls = []  # List of (checkbox, factor_edit, series)
        
        for i, series in enumerate(all_series):
            y_pos = 5 + i * row_height
            
            # Checkbox
            chk = vcl.TCheckBox(scroll_box)
            chk.Parent = scroll_box
            chk.Left = 15
            chk.Top = y_pos + 3
            chk.Width = 20
            chk.Caption = ""
            # Check only the base series by default
            chk.Checked = (series == base_series)
            
            # Factor edit
            edt_factor = vcl.TEdit(scroll_box)
            edt_factor.Parent = scroll_box
            edt_factor.Left = 60
            edt_factor.Top = y_pos
            edt_factor.Width = 80
            edt_factor.Text = "1.00"
            
            # Series legend label
            legend = series.LegendText
            if len(legend) > 50:
                legend = legend[:47] + "..."
            
            lbl_legend = vcl.TLabel(scroll_box)
            lbl_legend.Parent = scroll_box
            lbl_legend.Left = 160
            lbl_legend.Top = y_pos + 3
            lbl_legend.Caption = legend
            lbl_legend.Width = 280
            
            # Highlight base series
            if series == base_series:
                lbl_legend.Font.Style = {"fsBold"}
                lbl_legend.Font.Color = 0x800000
            
            labels.append(lbl_legend)
            series_controls.append((chk, edt_factor, series))
        
        # Footer section
        footer_top = 100 + content_height + 10
        
        # Separator
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = footer_top
        sep3.Width = 470
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        # Output color
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Result color:"
        lbl_color.Left = 20
        lbl_color.Top = footer_top + 15
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 120
        cb_color.Top = footer_top + 12
        cb_color.Width = 100
        cb_color.Selected = 0xFF0000  # Red by default
        
        # Separator before buttons
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10
        sep4.Top = footer_top + 50
        sep4.Width = 470
        sep4.Height = 2
        sep4.Shape = "bsTopLine"
        
        # Buttons
        btn_apply = vcl.TButton(Form)
        btn_apply.Parent = Form
        btn_apply.Caption = "Combine"
        btn_apply.ModalResult = 1
        btn_apply.Default = True
        btn_apply.Left = 150
        btn_apply.Top = footer_top + 65
        btn_apply.Width = 100
        btn_apply.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        btn_cancel.Left = 260
        btn_cancel.Top = footer_top + 65
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        if Form.ShowModal() == 1:
            try:
                # Collect selected series and factors
                selected_series = []
                factors = []
                legend_parts = []
                
                for chk, edt_factor, series in series_controls:
                    if chk.Checked:
                        try:
                            factor = float(edt_factor.Text)
                        except ValueError:
                            show_error(f"Invalid factor for series '{series.LegendText[:30]}'", 
                                       "Linear Combination")
                            return
                        
                        selected_series.append(series)
                        factors.append(factor)
                        
                        # Build legend part
                        short_legend = series.LegendText[:20] if len(series.LegendText) > 20 else series.LegendText
                        if factor >= 0:
                            sign = "+" if legend_parts else ""
                            legend_parts.append(f"{sign}{factor:.2g}·({short_legend})")
                        else:
                            legend_parts.append(f"{factor:.2g}·({short_legend})")
                
                if not selected_series:
                    show_error("Select at least one series.", "Linear Combination")
                    return
                
                # Calculate combined Y values
                y_combined = np.zeros(len(x_base))
                
                for series, factor in zip(selected_series, factors):
                    points = series.Points
                    x_series = np.array([p.x for p in points])
                    y_series = np.array([p.y for p in points])
                    
                    if series == base_series:
                        # Use original Y values directly
                        y_interp = y_series
                    else:
                        # Interpolate Y values at base X positions
                        try:
                            cs = CubicSpline(x_series, y_series, extrapolate=True)
                            y_interp = cs(x_base)
                        except Exception as e:
                            show_error(f"Interpolation error for '{series.LegendText[:30]}': {str(e)}", 
                                       "Linear Combination")
                            return
                    
                    y_combined += factor * y_interp
                
                # Create result series
                new_points = [Point(float(x), float(y)) for x, y in zip(x_base, y_combined)]
                
                new_series = Graph.TPointSeries()
                new_series.PointType = Graph.ptCartesian
                new_series.Points = new_points
                new_series.LegendText = " ".join(legend_parts) if legend_parts else "Linear Combination"
                new_series.Size = 0
                new_series.Style = 0
                new_series.LineSize = 1
                new_series.ShowLabels = False
                
                color = int(cb_color.Selected) & 0xFFFFFF
                color_val = safe_color(color)
                new_series.FillColor = color_val
                new_series.FrameColor = color_val
                new_series.LineColor = color_val
                
                Graph.FunctionList.append(new_series)
                Graph.Update()
                
            except Exception as e:
                show_error(f"Error combining series: {str(e)}", "Linear Combination")
    
    finally:
        Form.Free()


# Create action for menu
LinearCombinationAction = Graph.CreateAction(
    Caption="Linear Combination...",
    OnExecute=linear_combination,
    Hint="Combines point series linearly: y = Σ kᵢ·yᵢ",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "LinearCombination_sm.png")
)

# Add action to Plugins menu
Graph.AddActionToMainMenu(LinearCombinationAction, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"]) # type: ignore
