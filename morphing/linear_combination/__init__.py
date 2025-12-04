# Plugin to combine point series linearly or by product
import os

# Import common module
from common import (
    setup_venv, get_selected_point_series, show_error, show_info, 
    safe_color, Point, Graph, vcl, get_visible_point_series,
    get_series_data_np, resample_to_base
)

setup_venv()

import numpy as np

PluginName = "Linear Combination"
PluginVersion = "1.1"
PluginDescription = "Combines point series: Summatory y = Σ kᵢ·yᵢ or Productory y = Π yᵢⁿⁱ"


def linear_combination(Action):
    """Opens dialog to combine point series linearly or by product."""
    
    # Get selected series (base series)
    base_series, error_msg = get_selected_point_series()
    if base_series is None:
        show_error(error_msg or "You must select a point series (TPointSeries) as base.", 
                   "Series Combination")
        return
    
    # Get all visible point series
    all_series = get_visible_point_series()
    if len(all_series) < 1:
        show_error("No visible point series found.", "Series Combination")
        return
    
    # Get base series X values using common utility
    x_base, y_base_orig = get_series_data_np(base_series)
    if len(x_base) < 2:
        show_error("Base series must have at least 2 points.", "Series Combination")
        return
    
    # Calculate form height based on number of series
    row_height = 30
    header_height = 170  # Increased for operation type selection
    footer_height = 120
    max_visible_rows = 10
    visible_rows = min(len(all_series), max_visible_rows)
    content_height = visible_rows * row_height + 10
    form_height = header_height + content_height + footer_height
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Series Combination"
        Form.Width = 500
        Form.Height = form_height
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []
        
        # Header info
        lbl_title = vcl.TLabel(Form)
        lbl_title.Parent = Form
        lbl_title.Caption = "Combine series"
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
        sep0 = vcl.TBevel(Form)
        sep0.Parent = Form
        sep0.Left = 10
        sep0.Top = 65
        sep0.Width = 470
        sep0.Height = 2
        sep0.Shape = "bsTopLine"
        
        # Operation type selection
        lbl_op_type = vcl.TLabel(Form)
        lbl_op_type.Parent = Form
        lbl_op_type.Caption = "Operation Type:"
        lbl_op_type.Left = 20
        lbl_op_type.Top = 75
        lbl_op_type.Font.Style = {"fsBold"}
        labels.append(lbl_op_type)
        
        rb_summatory = vcl.TRadioButton(Form)
        rb_summatory.Parent = Form
        rb_summatory.Caption = "Summatory: y = Σ kᵢ · yᵢ(x)"
        rb_summatory.Left = 40
        rb_summatory.Top = 95
        rb_summatory.Width = 200
        rb_summatory.Checked = True
        
        rb_productory = vcl.TRadioButton(Form)
        rb_productory.Parent = Form
        rb_productory.Caption = "Productory: y = Π yᵢ(x)ⁿⁱ"
        rb_productory.Left = 260
        rb_productory.Top = 95
        rb_productory.Width = 200
        
        # Separator
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 120
        sep1.Width = 470
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Column headers
        lbl_col_sel = vcl.TLabel(Form)
        lbl_col_sel.Parent = Form
        lbl_col_sel.Caption = "Use"
        lbl_col_sel.Left = 25
        lbl_col_sel.Top = 130
        lbl_col_sel.Font.Style = {"fsBold"}
        labels.append(lbl_col_sel)
        
        lbl_col_factor = vcl.TLabel(Form)
        lbl_col_factor.Parent = Form
        lbl_col_factor.Caption = "Factor (kᵢ)"
        lbl_col_factor.Left = 70
        lbl_col_factor.Top = 130
        lbl_col_factor.Font.Style = {"fsBold"}
        labels.append(lbl_col_factor)
        
        lbl_col_series = vcl.TLabel(Form)
        lbl_col_series.Parent = Form
        lbl_col_series.Caption = "Series"
        lbl_col_series.Left = 170
        lbl_col_series.Top = 130
        lbl_col_series.Font.Style = {"fsBold"}
        labels.append(lbl_col_series)
        
        # Separator under headers
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 150
        sep2.Width = 470
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        # Scrollable area for series
        scroll_box = vcl.TScrollBox(Form)
        scroll_box.Parent = Form
        scroll_box.Left = 10
        scroll_box.Top = 155
        scroll_box.Width = 465
        scroll_box.Height = content_height
        scroll_box.BorderStyle = "bsNone"
        
        # Function to update column header based on operation type
        def on_operation_change(Sender):
            if rb_summatory.Checked:
                lbl_col_factor.Caption = "Factor (kᵢ)"
            else:
                lbl_col_factor.Caption = "Exponent (nᵢ)"
        
        rb_summatory.OnClick = on_operation_change
        rb_productory.OnClick = on_operation_change
        
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
        footer_top = 155 + content_height + 10
        
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
                # Determine operation type
                is_summatory = rb_summatory.Checked
                
                # Collect selected series and factors/exponents
                selected_series = []
                values = []  # factors for summatory, exponents for productory
                legend_parts = []
                
                for chk, edt_factor, series in series_controls:
                    if chk.Checked:
                        try:
                            value = float(edt_factor.Text)
                        except ValueError:
                            value_name = "factor" if is_summatory else "exponent"
                            show_error(f"Invalid {value_name} for series '{series.LegendText[:30]}'", 
                                       "Series Combination")
                            return
                        
                        selected_series.append(series)
                        values.append(value)
                        
                        # Build legend part
                        short_legend = series.LegendText[:20] if len(series.LegendText) > 20 else series.LegendText
                        if is_summatory:
                            if value >= 0:
                                sign = "+" if legend_parts else ""
                                legend_parts.append(f"{sign}{value:.2g}·({short_legend})")
                            else:
                                legend_parts.append(f"{value:.2g}·({short_legend})")
                        else:
                            # Productory legend
                            if value == 1.0:
                                legend_parts.append(f"({short_legend})")
                            else:
                                legend_parts.append(f"({short_legend})^{value:.2g}")
                
                if not selected_series:
                    show_error("Select at least one series.", "Series Combination")
                    return
                
                # Calculate combined Y values
                if is_summatory:
                    y_combined = np.zeros(len(x_base))
                else:
                    y_combined = np.ones(len(x_base))
                
                for series, value in zip(selected_series, values):
                    x_series, y_series = get_series_data_np(series)
                    
                    if series == base_series:
                        # Use original Y values directly
                        y_interp = y_series
                    else:
                        # Interpolate Y values at base X positions using common utility
                        try:
                            y_interp = resample_to_base(x_base, x_series, y_series, method='cubic')
                        except Exception as e:
                            show_error(f"Interpolation error for '{series.LegendText[:30]}': {str(e)}", 
                                       "Series Combination")
                            return
                    
                    if is_summatory:
                        y_combined += value * y_interp
                    else:
                        # Productory: multiply by y^exponent
                        y_combined *= np.power(y_interp, value)
                
                # Create result series
                new_points = [Point(float(x), float(y)) for x, y in zip(x_base, y_combined)]
                
                new_series = Graph.TPointSeries()
                new_series.PointType = Graph.ptCartesian
                new_series.Points = new_points
                
                if is_summatory:
                    new_series.LegendText = " ".join(legend_parts) if legend_parts else "Summatory"
                else:
                    new_series.LegendText = " × ".join(legend_parts) if legend_parts else "Productory"
                
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
                show_error(f"Error combining series: {str(e)}", "Series Combination")
    
    finally:
        Form.Free()


# Create action for menu
LinearCombinationAction = Graph.CreateAction(
    Caption="Series Combination...",
    OnExecute=linear_combination,
    Hint="Combines point series: Summatory y = Σ kᵢ·yᵢ or Productory y = Π yᵢⁿⁱ",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "LinearCombination_sm.png")
)

# Add action to Plugins menu
Graph.AddActionToMainMenu(LinearCombinationAction, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"]) # type: ignore
