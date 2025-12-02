# Plugin to apply custom functions to X and Y values of a point series
# Generates: [Xnew] = g([X]) = [g(x0), g(x1), ..., g(xn)]
#            [Ynew] = f([Y]) = [f(y0), f(y1), ..., f(yn)]
import os
import re

import Graph
import vcl  # type: ignore

# Import common utilities
from common import (
    get_selected_point_series, show_error, get_series_data, 
    Point, safe_color
)

PluginName = "Apply Function"
PluginVersion = "1.1"
PluginDescription = "Applies custom functions f(y) and g(x) to transform X and Y values of the selected point series."


def apply_function_to_series(Action):
    """
    Shows a dialog to apply a custom function to the Y values of the selected series.
    """
    # Get selected series
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "Apply Function")
        return

    # Get current data
    x_vals, y_vals = get_series_data(series)
    
    if not y_vals:
        show_error("The selected series has no points.", "Apply Function")
        return

    n_points = len(y_vals)
    y_min = min(y_vals)
    y_max = max(y_vals)

    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Apply Function to Series"
        Form.Width = 450
        Form.Height = 570
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []  # Keep references
        
        # Help panel at top
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
        lbl_help_title.Caption = "Apply Function"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        lbl_help = vcl.TLabel(help_panel)
        lbl_help.Parent = help_panel
        lbl_help.Caption = "Transforms: [Xnew, Ynew] = [g(x), f(y)]"
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)

        # Separator
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 75
        sep1.Width = 420
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Series info section
        lbl_info = vcl.TLabel(Form)
        lbl_info.Parent = Form
        lbl_info.Caption = "Selected Series"
        lbl_info.Left = 10
        lbl_info.Top = 85
        lbl_info.Font.Style = {"fsBold"}
        labels.append(lbl_info)
        
        # Series name and stats
        series_name = series.LegendText if series.LegendText else "(unnamed)"
        lbl_series = vcl.TLabel(Form)
        lbl_series.Parent = Form
        lbl_series.Caption = f"{series_name}  |  {n_points} points  |  Y ∈ [{y_min:.4g}, {y_max:.4g}]"
        lbl_series.Left = 20
        lbl_series.Top = 108
        lbl_series.Font.Color = 0x666666
        labels.append(lbl_series)

        # Separator
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 135
        sep2.Width = 420
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        # Function input section
        lbl_func = vcl.TLabel(Form)
        lbl_func.Parent = Form
        lbl_func.Caption = "Functions"
        lbl_func.Left = 10
        lbl_func.Top = 145
        lbl_func.Font.Style = {"fsBold"}
        labels.append(lbl_func)
        
        # Function Y input label
        lbl_input_y = vcl.TLabel(Form)
        lbl_input_y.Parent = Form
        lbl_input_y.Caption = "f(y) ="
        lbl_input_y.Left = 20
        lbl_input_y.Top = 173
        labels.append(lbl_input_y)
        
        # Function Y input field
        edt_function_y = vcl.TEdit(Form)
        edt_function_y.Parent = Form
        edt_function_y.Left = 60
        edt_function_y.Top = 170
        edt_function_y.Width = 360
        edt_function_y.Text = "y"  # Identity function by default
        
        # Function X input label
        lbl_input_x = vcl.TLabel(Form)
        lbl_input_x.Parent = Form
        lbl_input_x.Caption = "g(x) ="
        lbl_input_x.Left = 20
        lbl_input_x.Top = 203
        labels.append(lbl_input_x)
        
        # Function X input field
        edt_function_x = vcl.TEdit(Form)
        edt_function_x.Parent = Form
        edt_function_x.Left = 60
        edt_function_x.Top = 200
        edt_function_x.Width = 360
        edt_function_x.Text = "x"  # Identity function by default
        
        # Examples panel
        pnl_examples = vcl.TPanel(Form)
        pnl_examples.Parent = Form
        pnl_examples.Left = 20
        pnl_examples.Top = 230
        pnl_examples.Width = 400
        pnl_examples.Height = 85
        pnl_examples.BevelOuter = "bvLowered"
        pnl_examples.Color = 0xF8FFF8
        
        examples_text = (
            "Examples:  y^2  |  sqrt(y)  |  abs(y)  |  ln(y)  |  10*y + 5\n"
            "           sin(x)  |  e^(-x)  |  x + 3.3  |  x*cos(x)\n"
            "Use 'y' for f(y) and 'x' for g(x). Graph syntax applies."
        )
        lbl_examples = vcl.TLabel(pnl_examples)
        lbl_examples.Parent = pnl_examples
        lbl_examples.Caption = examples_text
        lbl_examples.Left = 10
        lbl_examples.Top = 12
        lbl_examples.Font.Color = 0x006400
        labels.append(lbl_examples)

        # Separator
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 325
        sep3.Width = 420
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        # Output section
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output"
        lbl_output.Left = 10
        lbl_output.Top = 335
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Panel to group output radio buttons
        pnl_output = vcl.TPanel(Form)
        pnl_output.Parent = Form
        pnl_output.Left = 10
        pnl_output.Top = 355
        pnl_output.Width = 420
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
        rb_replace.Left = 200
        rb_replace.Top = 5
        
        # Color for new series
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Color (new series):"
        lbl_color.Left = 20
        lbl_color.Top = 393
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 140
        cb_color.Top = 390
        cb_color.Width = 100
        cb_color.Selected = 0x00AA00  # Green by default

        # Separator before buttons
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10
        sep4.Top = 430
        sep4.Width = 420
        sep4.Height = 2
        sep4.Shape = "bsTopLine"
        
        # Buttons
        btn_apply = vcl.TButton(Form)
        btn_apply.Parent = Form
        btn_apply.Caption = "Apply"
        btn_apply.ModalResult = 1  # mrOk
        btn_apply.Default = True
        btn_apply.Left = 130
        btn_apply.Top = 450
        btn_apply.Width = 100
        btn_apply.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 240
        btn_cancel.Top = 450
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # Show dialog
        if Form.ShowModal() == 1:
            try:
                func_y_text = edt_function_y.Text.strip()
                func_x_text = edt_function_x.Text.strip()
                
                if not func_y_text:
                    func_y_text = "y"  # Default to identity
                if not func_x_text:
                    func_x_text = "x"  # Default to identity
                
                # Apply functions to each X and Y value
                new_x_vals = []
                new_y_vals = []
                errors = []
                
                for i, (x, y) in enumerate(zip(x_vals, y_vals)):
                    try:
                        # Replace 'y' with the actual value for f(y)
                        expr_y = re.sub(r'\by\b', f'({y})', func_y_text)
                        new_y = float(Graph.Eval(expr_y))
                        
                        # Replace 'x' with the actual value for g(x)
                        expr_x = re.sub(r'\bx\b', f'({x})', func_x_text)
                        new_x = float(Graph.Eval(expr_x))
                        
                        new_x_vals.append(new_x)
                        new_y_vals.append(new_y)
                    except Exception as e:
                        errors.append(f"x={x:.4g}, y={y:.4g}: {str(e)}")
                        new_x_vals.append(float('nan'))
                        new_y_vals.append(float('nan'))
                
                # Check for errors
                import math
                valid_count = sum(1 for x, y in zip(new_x_vals, new_y_vals) 
                                  if not math.isnan(x) and not math.isnan(y))
                
                if valid_count == 0:
                    error_preview = "\n".join(errors[:3])
                    if len(errors) > 3:
                        error_preview += "\n..."
                    raise ValueError(f"No valid points could be generated.\n\nErrors:\n{error_preview}")
                
                # Create new points (filter out NaN values)
                new_points = [
                    Point(new_x, new_y) 
                    for new_x, new_y in zip(new_x_vals, new_y_vals) 
                    if not math.isnan(new_x) and not math.isnan(new_y)
                ]
                
                # Build legend suffix
                legend_parts = []
                if func_y_text != "y":
                    legend_parts.append(f"f(y)={func_y_text}")
                if func_x_text != "x":
                    legend_parts.append(f"g(x)={func_x_text}")
                legend_suffix = f" [{', '.join(legend_parts)}]" if legend_parts else ""
                
                if rb_new.Checked:
                    # Create new series
                    new_series = Graph.TPointSeries()
                    new_series.PointType = series.PointType
                    new_series.Points = new_points
                    
                    # Copy display properties
                    original_legend = series.LegendText if series.LegendText else "Series"
                    new_series.LegendText = f"{original_legend}{legend_suffix}"
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
                    # Update legend
                    if series.LegendText and legend_suffix:
                        series.LegendText = f"{series.LegendText}{legend_suffix}"
                
                Graph.Update()
                
            except ValueError as e:
                show_error(str(e), "Apply Function")
            except Exception as e:
                show_error(f"Error applying function: {str(e)}", "Apply Function")
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="Apply Function...", 
    OnExecute=apply_function_to_series, 
    Hint="Apply custom functions f(y) and g(x) to transform X and Y values of the selected series",
    IconFile=os.path.join(os.path.dirname(__file__), "ApplyFunction_sm.png")
)

# Add to Plugins -> Morphing menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"])  # type: ignore
