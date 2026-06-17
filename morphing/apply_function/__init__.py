# Plugin to apply custom functions to X and Y values of a point series
# Generates: [Xnew] = g([X]) = [g(x0), g(x1), ..., g(xn)]
#            [Ynew] = f([Y]) = [f(y0), f(y1), ..., f(yn)]
import os
import re
import math

import Graph
import vcl  # type: ignore

# Import common utilities
from common import (
    get_selected_point_series, show_error, show_info, get_series_data,
    Point, safe_color, get_visible_point_series
)

PluginName = "Apply Function"
PluginVersion = "1.2"
PluginDescription = "Applies custom functions f(y) and g(x) to transform X and Y values of the selected point series."


def apply_function_to_series(Action):
    """
    Shows a dialog to apply a custom function to the X/Y values of the target series.
    """
    # Get selected series (drives range defaults and is pre-checked as target)
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
    x_min = min(x_vals)
    x_max = max(x_vals)
    y_min = min(y_vals)
    y_max = max(y_vals)

    # All visible series are candidate targets
    visible_series = get_visible_point_series()

    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Apply Function to Series"
        Form.Width = 450
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

        # ── Target section ────────────────────────────────────────────
        lbl_target = vcl.TLabel(Form)
        lbl_target.Parent = Form
        lbl_target.Caption = "Target"
        lbl_target.Left = 10
        lbl_target.Top = 85
        lbl_target.Font.Style = {"fsBold"}
        labels.append(lbl_target)

        scroll_height = min(len(visible_series) * 22 + 4, 110) if visible_series else 24
        scroll_box = vcl.TScrollBox(Form)
        scroll_box.Parent = Form
        scroll_box.Left = 10
        scroll_box.Top = 107
        scroll_box.Width = 420
        scroll_box.Height = scroll_height
        scroll_box.BorderStyle = "bsSingle"

        series_checks = []  # List of (checkbox, series) tuples
        for i, vs in enumerate(visible_series):
            chk = vcl.TCheckBox(scroll_box)
            chk.Parent = scroll_box
            chk.Left = 10
            chk.Top = i * 22 + 2
            chk.Width = 390
            chk.Caption = vs.LegendText if vs.LegendText else f"Series {i + 1}"
            chk.Checked = (vs == series)
            series_checks.append((chk, vs))

        y = 107 + scroll_height + 10

        # Reference (selected series) info
        series_name = series.LegendText if series.LegendText else "(unnamed)"
        lbl_series = vcl.TLabel(Form)
        lbl_series.Parent = Form
        lbl_series.Caption = f"Reference: {series_name}  |  {n_points} points"
        lbl_series.Left = 20
        lbl_series.Top = y
        lbl_series.Font.Color = 0x666666
        labels.append(lbl_series)

        lbl_series_range = vcl.TLabel(Form)
        lbl_series_range.Parent = Form
        lbl_series_range.Caption = f"X ∈ [{x_min:.4g}, {x_max:.4g}]  |  Y ∈ [{y_min:.4g}, {y_max:.4g}]"
        lbl_series_range.Left = 20
        lbl_series_range.Top = y + 18
        lbl_series_range.Font.Color = 0x666666
        labels.append(lbl_series_range)

        y += 42

        # Separator
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = y
        sep2.Width = 420
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        y += 10

        # Range limits section
        lbl_range = vcl.TLabel(Form)
        lbl_range.Parent = Form
        lbl_range.Caption = "Apply to Range (points outside range are copied unchanged)"
        lbl_range.Left = 10
        lbl_range.Top = y
        lbl_range.Font.Style = {"fsBold"}
        labels.append(lbl_range)
        y += 28

        # X range
        lbl_xrange = vcl.TLabel(Form)
        lbl_xrange.Parent = Form
        lbl_xrange.Caption = "X from:"
        lbl_xrange.Left = 20
        lbl_xrange.Top = y + 3
        labels.append(lbl_xrange)

        edt_x_min = vcl.TEdit(Form)
        edt_x_min.Parent = Form
        edt_x_min.Left = 70
        edt_x_min.Top = y
        edt_x_min.Width = 100
        edt_x_min.Text = f"{x_min:.6g}"

        lbl_xto = vcl.TLabel(Form)
        lbl_xto.Parent = Form
        lbl_xto.Caption = "to:"
        lbl_xto.Left = 180
        lbl_xto.Top = y + 3
        labels.append(lbl_xto)

        edt_x_max = vcl.TEdit(Form)
        edt_x_max.Parent = Form
        edt_x_max.Left = 205
        edt_x_max.Top = y
        edt_x_max.Width = 100
        edt_x_max.Text = f"{x_max:.6g}"
        y += 30

        # Y range
        lbl_yrange = vcl.TLabel(Form)
        lbl_yrange.Parent = Form
        lbl_yrange.Caption = "Y from:"
        lbl_yrange.Left = 20
        lbl_yrange.Top = y + 3
        labels.append(lbl_yrange)

        edt_y_min = vcl.TEdit(Form)
        edt_y_min.Parent = Form
        edt_y_min.Left = 70
        edt_y_min.Top = y
        edt_y_min.Width = 100
        edt_y_min.Text = f"{y_min:.6g}"

        lbl_yto = vcl.TLabel(Form)
        lbl_yto.Parent = Form
        lbl_yto.Caption = "to:"
        lbl_yto.Left = 180
        lbl_yto.Top = y + 3
        labels.append(lbl_yto)

        edt_y_max = vcl.TEdit(Form)
        edt_y_max.Parent = Form
        edt_y_max.Left = 205
        edt_y_max.Top = y
        edt_y_max.Width = 100
        edt_y_max.Text = f"{y_max:.6g}"
        y += 32

        # Separator
        sep2b = vcl.TBevel(Form)
        sep2b.Parent = Form
        sep2b.Left = 10
        sep2b.Top = y
        sep2b.Width = 420
        sep2b.Height = 2
        sep2b.Shape = "bsTopLine"
        y += 10

        # Function input section
        lbl_func = vcl.TLabel(Form)
        lbl_func.Parent = Form
        lbl_func.Caption = "Functions"
        lbl_func.Left = 10
        lbl_func.Top = y
        lbl_func.Font.Style = {"fsBold"}
        labels.append(lbl_func)
        y += 28

        # Function Y input label
        lbl_input_y = vcl.TLabel(Form)
        lbl_input_y.Parent = Form
        lbl_input_y.Caption = "f(y) ="
        lbl_input_y.Left = 20
        lbl_input_y.Top = y + 3
        labels.append(lbl_input_y)

        # Function Y input field
        edt_function_y = vcl.TEdit(Form)
        edt_function_y.Parent = Form
        edt_function_y.Left = 60
        edt_function_y.Top = y
        edt_function_y.Width = 360
        edt_function_y.Text = "y"  # Identity function by default
        y += 30

        # Function X input label
        lbl_input_x = vcl.TLabel(Form)
        lbl_input_x.Parent = Form
        lbl_input_x.Caption = "g(x) ="
        lbl_input_x.Left = 20
        lbl_input_x.Top = y + 3
        labels.append(lbl_input_x)

        # Function X input field
        edt_function_x = vcl.TEdit(Form)
        edt_function_x.Parent = Form
        edt_function_x.Left = 60
        edt_function_x.Top = y
        edt_function_x.Width = 360
        edt_function_x.Text = "x"  # Identity function by default
        y += 30

        # Examples panel
        pnl_examples = vcl.TPanel(Form)
        pnl_examples.Parent = Form
        pnl_examples.Left = 20
        pnl_examples.Top = y
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
        y += 95

        # Separator
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = y
        sep3.Width = 420
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        y += 10

        # Output section
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output"
        lbl_output.Left = 10
        lbl_output.Top = y
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        y += 22

        # Panel to group output radio buttons
        pnl_output = vcl.TPanel(Form)
        pnl_output.Parent = Form
        pnl_output.Left = 10
        pnl_output.Top = y
        pnl_output.Width = 420
        pnl_output.Height = 30
        pnl_output.BevelOuter = "bvNone"

        rb_new = vcl.TRadioButton(Form)
        rb_new.Parent = pnl_output
        rb_new.Caption = "Create new series  (same color as original)"
        rb_new.Left = 10
        rb_new.Top = 5
        rb_new.Width = 280
        rb_new.Checked = True

        rb_replace = vcl.TRadioButton(Form)
        rb_replace.Parent = pnl_output
        rb_replace.Caption = "Replace original"
        rb_replace.Left = 295
        rb_replace.Top = 5
        rb_replace.Width = 120
        y += 40

        # Separator before buttons
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10
        sep4.Top = y
        sep4.Width = 420
        sep4.Height = 2
        sep4.Shape = "bsTopLine"
        y += 12

        # Buttons
        btn_apply = vcl.TButton(Form)
        btn_apply.Parent = Form
        btn_apply.Caption = "Apply"
        btn_apply.ModalResult = 1  # mrOk
        btn_apply.Default = True
        btn_apply.Left = 130
        btn_apply.Top = y
        btn_apply.Width = 100
        btn_apply.Height = 30

        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 240
        btn_cancel.Top = y
        btn_cancel.Width = 100
        btn_cancel.Height = 30

        Form.Height = y + 75

        # Show dialog
        if Form.ShowModal() == 1:
            try:
                func_y_text = edt_function_y.Text.strip()
                func_x_text = edt_function_x.Text.strip()

                if not func_y_text:
                    func_y_text = "y"  # Default to identity
                if not func_x_text:
                    func_x_text = "x"  # Default to identity

                # Get range limits
                range_x_min = float(edt_x_min.Text)
                range_x_max = float(edt_x_max.Text)
                range_y_min = float(edt_y_min.Text)
                range_y_max = float(edt_y_max.Text)

                # Collect selected target series
                targets = [s for chk, s in series_checks if chk.Checked]
                if not targets:
                    raise ValueError("Select at least one target series.")

                # Build legend suffix
                legend_parts = []
                if func_y_text != "y":
                    legend_parts.append(f"f(y)={func_y_text}")
                if func_x_text != "x":
                    legend_parts.append(f"g(x)={func_x_text}")
                legend_suffix = f" [{', '.join(legend_parts)}]" if legend_parts else ""

                processed = 0
                failed = []  # series names that produced no valid points

                for tgt in targets:
                    t_x, t_y = get_series_data(tgt)
                    if not t_y:
                        continue

                    # Apply functions to each X and Y value of this target
                    new_x_vals = []
                    new_y_vals = []

                    for x, y_val in zip(t_x, t_y):
                        in_range = (range_x_min <= x <= range_x_max) and (range_y_min <= y_val <= range_y_max)

                        if in_range:
                            try:
                                expr_y = re.sub(r'\by\b', f'({y_val})', func_y_text)
                                new_y = float(Graph.Eval(expr_y))

                                expr_x = re.sub(r'\bx\b', f'({x})', func_x_text)
                                new_x = float(Graph.Eval(expr_x))

                                new_x_vals.append(new_x)
                                new_y_vals.append(new_y)
                            except Exception:
                                new_x_vals.append(float('nan'))
                                new_y_vals.append(float('nan'))
                        else:
                            # Point outside range - copy unchanged
                            new_x_vals.append(x)
                            new_y_vals.append(y_val)

                    # Create new points (filter out NaN values)
                    new_points = [
                        Point(nx, ny)
                        for nx, ny in zip(new_x_vals, new_y_vals)
                        if not math.isnan(nx) and not math.isnan(ny)
                    ]

                    if not new_points:
                        failed.append(tgt.LegendText if tgt.LegendText else "Series")
                        continue

                    if rb_new.Checked:
                        # Create new series (same color as the original)
                        new_series = Graph.TPointSeries()
                        new_series.PointType = tgt.PointType
                        new_series.Points = new_points

                        original_legend = tgt.LegendText if tgt.LegendText else "Series"
                        new_series.LegendText = f"{original_legend}{legend_suffix}"
                        new_series.Size = tgt.Size
                        new_series.Style = tgt.Style
                        new_series.LineSize = tgt.LineSize
                        new_series.ShowLabels = tgt.ShowLabels

                        color_val = safe_color(tgt.LineColor)
                        new_series.FillColor = color_val
                        new_series.FrameColor = color_val
                        new_series.LineColor = color_val

                        Graph.FunctionList.append(new_series)
                    else:
                        # Replace points in original series
                        tgt.Points = new_points
                        if tgt.LegendText and legend_suffix:
                            tgt.LegendText = f"{tgt.LegendText}{legend_suffix}"

                    processed += 1

                if processed == 0:
                    raise ValueError("No valid points could be generated for any selected series.")

                Graph.Update()

                if failed:
                    show_info(
                        f"Applied to {processed} series.\n\nSkipped (no valid points): {', '.join(failed)}",
                        "Apply Function"
                    )

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
