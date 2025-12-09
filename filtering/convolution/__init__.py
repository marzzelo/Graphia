# Plugin Convolution - Convolves a signal with a kernel (TPointSeries or TStdFunc)
# Uses scipy.signal.convolve for the convolution operation.

"""
Convolution Plugin - Convolves a selected point series with another series or function.
If a TStdFunc is selected as kernel, it is sampled at the same rate as the signal.
"""

import os
import math

import Graph
import vcl  # type: ignore

# Import numpy and scipy
import numpy as np
from scipy.signal import convolve

# Import common utilities
from common import (
    get_selected_point_series, show_error, show_info,
    get_series_data, Point, safe_color, get_series_stats,
    get_all_point_series, sample_std_function
)

PluginName = "Convolution"
PluginVersion = "1.0"
PluginDescription = "Convolve signal with a kernel (point series or sampled function)"


def get_all_std_functions():
    """
    Returns a list of all TStdFunc objects in the graph.
    
    Returns:
        list: List of TStdFunc objects
    """
    func_list = []
    for item in Graph.FunctionList:
        if type(item).__name__ == "TStdFunc":
            func_list.append(item)
    return func_list


def convolution_dialog(Action):
    """
    Shows a dialog to configure and perform convolution on the selected series.
    """
    # Get selected series (the signal to convolve)
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "Convolution")
        return

    # Get current signal data
    x_vals, y_vals = get_series_data(series)
    
    if len(y_vals) < 3:
        show_info("The selected series must have at least 3 points.", "Convolution")
        return

    # Calculate stats for defaults
    stats = get_series_stats(series)
    n_points = stats['n_points']
    x_min = stats['x_min']
    x_max = stats['x_max']
    dx_avg = stats['dx_avg']
    
    # Estimate sample rate from average dx
    if dx_avg > 0:
        srate = 1.0 / dx_avg
        ts = dx_avg
    else:
        srate = 1.0
        ts = 1.0
    
    # Get available kernels: other point series and std functions
    all_series = get_all_point_series()
    all_functions = get_all_std_functions()
    
    # Filter out the selected series itself from available kernels
    other_series = [s for s in all_series if s is not series]
    
    if len(other_series) == 0 and len(all_functions) == 0:
        show_error(
            "No kernel available.\n\n"
            "Add another point series or standard function to use as kernel.",
            "Convolution"
        )
        return
    
    # Build kernel list for dropdown: combine series and functions
    kernel_items = []  # List of tuples: (display_name, object, type)
    
    for s in other_series:
        name = s.LegendText if s.LegendText else "(unnamed series)"
        kernel_items.append((f"[Series] {name}", s, "series"))
    
    for f in all_functions:
        # Get function text
        func_text = None
        for attr in ['Text', 'LegendText']:
            if hasattr(f, attr):
                val = getattr(f, attr)
                if val and str(val) != 'f(x)':
                    func_text = str(val)
                    break
        if not func_text:
            func_text = "(unknown function)"
        kernel_items.append((f"[Func] {func_text}", f, "function"))
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Convolution (scipy.signal.convolve)"
        Form.Width = 500
        Form.Height = 480
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
        help_panel.Width = 470
        help_panel.Height = 70
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0

        lbl_help_title = vcl.TLabel(help_panel)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Convolution (scipy.signal.convolve)"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        series_name = series.LegendText if series.LegendText else "(unnamed)"
        lbl_series = vcl.TLabel(help_panel)
        lbl_series.Parent = help_panel
        lbl_series.Caption = f"Signal: {series_name}"
        lbl_series.Left = 10
        lbl_series.Top = 28
        lbl_series.Font.Color = 0x804000
        labels.append(lbl_series)
        
        lbl_info = vcl.TLabel(help_panel)
        lbl_info.Parent = help_panel
        lbl_info.Caption = f"n = {n_points} points  |  Ts ≈ {ts:.4G}  |  fs ≈ {srate:.4G} Hz"
        lbl_info.Left = 10
        lbl_info.Top = 48
        lbl_info.Font.Color = 0x804000
        labels.append(lbl_info)

        # =====================================================================
        # Kernel Selection Section
        # =====================================================================
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 90
        sep1.Width = 470
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        lbl_kernel_section = vcl.TLabel(Form)
        lbl_kernel_section.Parent = Form
        lbl_kernel_section.Caption = "Kernel Selection"
        lbl_kernel_section.Left = 10
        lbl_kernel_section.Top = 100
        lbl_kernel_section.Font.Style = {"fsBold"}
        labels.append(lbl_kernel_section)
        
        # Kernel dropdown
        lbl_kernel = vcl.TLabel(Form)
        lbl_kernel.Parent = Form
        lbl_kernel.Caption = "Kernel:"
        lbl_kernel.Left = 20
        lbl_kernel.Top = 128
        labels.append(lbl_kernel)
        
        cb_kernel = vcl.TComboBox(Form)
        cb_kernel.Parent = Form
        cb_kernel.Left = 100
        cb_kernel.Top = 125
        cb_kernel.Width = 370
        cb_kernel.Style = "csDropDownList"
        
        for item in kernel_items:
            cb_kernel.Items.Add(item[0])
        
        if len(kernel_items) > 0:
            cb_kernel.ItemIndex = 0
        
        # Kernel range (for functions)
        lbl_kernel_range = vcl.TLabel(Form)
        lbl_kernel_range.Parent = Form
        lbl_kernel_range.Caption = "Kernel X range (for functions):"
        lbl_kernel_range.Left = 20
        lbl_kernel_range.Top = 163
        labels.append(lbl_kernel_range)
        
        lbl_xmin = vcl.TLabel(Form)
        lbl_xmin.Parent = Form
        lbl_xmin.Caption = "Xmin:"
        lbl_xmin.Left = 220
        lbl_xmin.Top = 163
        labels.append(lbl_xmin)
        
        edt_xmin = vcl.TEdit(Form)
        edt_xmin.Parent = Form
        edt_xmin.Left = 260
        edt_xmin.Top = 160
        edt_xmin.Width = 80
        edt_xmin.Text = f"{-10*ts:.6G}"
        
        lbl_xmax = vcl.TLabel(Form)
        lbl_xmax.Parent = Form
        lbl_xmax.Caption = "Xmax:"
        lbl_xmax.Left = 350
        lbl_xmax.Top = 163
        labels.append(lbl_xmax)
        
        edt_xmax = vcl.TEdit(Form)
        edt_xmax.Parent = Form
        edt_xmax.Left = 390
        edt_xmax.Top = 160
        edt_xmax.Width = 80
        edt_xmax.Text = f"{10*ts:.6G}"

        # =====================================================================
        # Convolution Parameters Section
        # =====================================================================
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 195
        sep2.Width = 470
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        lbl_params = vcl.TLabel(Form)
        lbl_params.Parent = Form
        lbl_params.Caption = "Convolution Parameters"
        lbl_params.Left = 10
        lbl_params.Top = 205
        lbl_params.Font.Style = {"fsBold"}
        labels.append(lbl_params)
        
        # Mode selection
        lbl_mode = vcl.TLabel(Form)
        lbl_mode.Parent = Form
        lbl_mode.Caption = "Mode:"
        lbl_mode.Left = 20
        lbl_mode.Top = 235
        labels.append(lbl_mode)
        
        cb_mode = vcl.TComboBox(Form)
        cb_mode.Parent = Form
        cb_mode.Left = 100
        cb_mode.Top = 232
        cb_mode.Width = 120
        cb_mode.Style = "csDropDownList"
        cb_mode.Items.Add("same")
        cb_mode.Items.Add("full")
        cb_mode.Items.Add("valid")
        cb_mode.ItemIndex = 0  # same is default
        
        lbl_mode_info = vcl.TLabel(Form)
        lbl_mode_info.Parent = Form
        lbl_mode_info.Caption = "(output size)"
        lbl_mode_info.Left = 230
        lbl_mode_info.Top = 235
        lbl_mode_info.Font.Color = 0x666666
        labels.append(lbl_mode_info)
        
        # Method selection
        lbl_method = vcl.TLabel(Form)
        lbl_method.Parent = Form
        lbl_method.Caption = "Method:"
        lbl_method.Left = 20
        lbl_method.Top = 268
        labels.append(lbl_method)
        
        cb_method = vcl.TComboBox(Form)
        cb_method.Parent = Form
        cb_method.Left = 100
        cb_method.Top = 265
        cb_method.Width = 120
        cb_method.Style = "csDropDownList"
        cb_method.Items.Add("auto")
        cb_method.Items.Add("direct")
        cb_method.Items.Add("fft")
        cb_method.ItemIndex = 0  # auto is default
        
        lbl_method_info = vcl.TLabel(Form)
        lbl_method_info.Parent = Form
        lbl_method_info.Caption = "(computation method)"
        lbl_method_info.Left = 230
        lbl_method_info.Top = 268
        lbl_method_info.Font.Color = 0x666666
        labels.append(lbl_method_info)
        
        # Normalize kernel checkbox
        chk_normalize = vcl.TCheckBox(Form)
        chk_normalize.Parent = Form
        chk_normalize.Caption = "Normalize kernel (sum = 1)"
        chk_normalize.Left = 20
        chk_normalize.Top = 300
        chk_normalize.Checked = False

        # =====================================================================
        # Output Section
        # =====================================================================
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 335
        sep3.Width = 470
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output"
        lbl_output.Left = 10
        lbl_output.Top = 345
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Color selector
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Result color:"
        lbl_color.Left = 20
        lbl_color.Top = 375
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 100
        cb_color.Top = 372
        cb_color.Width = 100
        cb_color.Selected = 0x00AA00  # Green by default

        # =====================================================================
        # Buttons
        # =====================================================================
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10
        sep4.Top = 410
        sep4.Width = 470
        sep4.Height = 2
        sep4.Shape = "bsTopLine"
        
        btn_compute = vcl.TButton(Form)
        btn_compute.Parent = Form
        btn_compute.Caption = "Convolve"
        btn_compute.Left = 150
        btn_compute.Top = 420
        btn_compute.Width = 100
        btn_compute.Height = 30
        btn_compute.Default = True
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 260
        btn_cancel.Top = 420
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        def on_compute(Sender):
            try:
                # Get selected kernel
                kernel_idx = cb_kernel.ItemIndex
                if kernel_idx < 0:
                    show_error("Please select a kernel.", "Convolution")
                    return
                
                kernel_name, kernel_obj, kernel_type = kernel_items[kernel_idx]
                
                # Get kernel data
                if kernel_type == "series":
                    # Use the point series directly
                    k_x, k_y = get_series_data(kernel_obj)
                    kernel_data = np.array(k_y)
                else:
                    # Function: sample it using sample_std_function
                    try:
                        k_xmin = float(edt_xmin.Text)
                        k_xmax = float(edt_xmax.Text)
                    except ValueError:
                        show_error("Invalid kernel X range values.", "Convolution")
                        return
                    
                    if k_xmax <= k_xmin:
                        show_error("Xmax must be > Xmin.", "Convolution")
                        return
                    
                    try:
                        k_x, k_y, errors = sample_std_function(kernel_obj, ts, k_xmin, k_xmax)
                        # Filter NaN values
                        valid_k = [(x, y) for x, y in zip(k_x, k_y) if not math.isnan(y)]
                        if len(valid_k) < 2:
                            show_error("Kernel function could not be sampled properly.", "Convolution")
                            return
                        k_x = [p[0] for p in valid_k]
                        k_y = [p[1] for p in valid_k]
                        kernel_data = np.array(k_y)
                    except Exception as e:
                        show_error(f"Error sampling kernel function: {str(e)}", "Convolution")
                        return
                
                if len(kernel_data) < 2:
                    show_error("Kernel must have at least 2 points.", "Convolution")
                    return
                
                # Normalize kernel if requested
                if chk_normalize.Checked:
                    kernel_sum = np.sum(kernel_data)
                    if kernel_sum != 0:
                        kernel_data = kernel_data / kernel_sum
                
                # Get convolution parameters
                mode = cb_mode.Text.lower()
                method = cb_method.Text.lower()
                
                # Perform convolution
                signal_data = np.array(y_vals)
                result = convolve(signal_data, kernel_data, mode=mode, method=method)
                
                # Generate x values for result based on mode
                if mode == 'same':
                    result_x = x_vals
                elif mode == 'full':
                    # Full mode: length = len(signal) + len(kernel) - 1
                    n_result = len(result)
                    # x axis starts before original signal
                    x_start = x_min - (len(kernel_data) - 1) * dx_avg / 2
                    result_x = [x_start + i * dx_avg for i in range(n_result)]
                else:  # valid
                    # Valid mode: length = max(len(signal), len(kernel)) - min(len(signal), len(kernel)) + 1
                    n_result = len(result)
                    # x axis starts after kernel size offset
                    x_start = x_min + (len(kernel_data) - 1) * dx_avg / 2
                    result_x = [x_start + i * dx_avg for i in range(n_result)]
                
                # Create result series
                result_points = [Point(float(result_x[i]), float(result[i])) for i in range(len(result))]
                
                result_series = Graph.TPointSeries()
                result_series.Points = result_points
                
                original_legend = series.LegendText if series.LegendText else "Signal"
                kernel_short = kernel_name.split(']')[1].strip() if ']' in kernel_name else kernel_name
                result_series.LegendText = f"{original_legend} ⊛ {kernel_short}"
                
                result_series.Size = 0
                result_series.Style = 0
                result_series.LineSize = 2
                result_series.ShowLabels = False
                
                color_val = safe_color(cb_color.Selected)
                result_series.FillColor = color_val
                result_series.FrameColor = color_val
                result_series.LineColor = color_val
                
                Graph.FunctionList.append(result_series)
                Graph.Update()
                
                show_info(
                    f"Convolution completed:\n"
                    f"• Signal: {n_points} points\n"
                    f"• Kernel: {len(kernel_data)} points\n"
                    f"• Mode: {mode}\n"
                    f"• Result: {len(result)} points",
                    "Convolution"
                )
                
                Form.ModalResult = 1  # mrOk
                
            except Exception as e:
                show_error(f"Error performing convolution: {str(e)}", "Convolution")
        
        btn_compute.OnClick = on_compute
        
        # Show dialog
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="Convolution...", 
    OnExecute=convolution_dialog, 
    Hint="Convolve signal with a kernel (series or function)",
    IconFile=None
)

# Add to Plugins -> Filtering menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Filtering"])
