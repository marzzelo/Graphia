# Plugin to generate square wave signals using scipy.signal.square
import sys
import os

# Add virtual environment to path to find scipy/numpy
venv_site_packages = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".venv", "Lib", "site-packages")
if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
    sys.path.append(venv_site_packages)

import Graph
import vcl
import numpy as np
from scipy import signal
from collections import namedtuple

# Import common utilities
from common import (
    get_series_data, sample_std_function, Point, safe_color
)

PluginName = "Square Wave Generator"
PluginVersion = "1.0"
PluginDescription = "Generates square wave signals with variable duty cycle using scipy.signal.square."


def SquareWaveDialog(Action):
    """
    Opens a dialog to configure and generate square wave signals.
    """
    # Build list of available series and functions for duty cycle
    duty_sources = []  # List of (display_name, type, object)
    duty_sources.append(("Constant value", "constant", None))
    
    # Add all TPointSeries
    for item in Graph.FunctionList:
        if type(item).__name__ == "TPointSeries":
            name = item.LegendText if item.LegendText else "PointSeries"
            duty_sources.append((f"[Series] {name}", "series", item))
    
    # Add all TStdFunc - look for function text in multiple attributes
    for item in Graph.FunctionList:
        if type(item).__name__ == "TStdFunc":
            # Try to get the function expression from various attributes
            func_name = None
            for attr in ['Text', 'text', 'Equation', 'equation', 'Formula', 'formula']:
                if hasattr(item, attr):
                    val = getattr(item, attr)
                    if val and str(val) != 'f(x)':
                        func_name = str(val)
                        break
            if not func_name and item.LegendText:
                func_name = item.LegendText
            if not func_name:
                func_name = "Function"
            duty_sources.append((f"[Function] {func_name}", "function", item))
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Square Wave Generator"
        Form.Width = 500
        Form.Height = 520
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"

        inputs = {}
        labels = []  # Keep references to prevent GC

        # =====================================================================
        # Help panel at top
        # =====================================================================
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 10
        help_panel.Top = 10
        help_panel.Width = 470
        help_panel.Height = 55
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0

        lbl_help_title = vcl.TLabel(help_panel)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Square Wave Generator"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        lbl_help = vcl.TLabel(help_panel)
        lbl_help.Parent = help_panel
        lbl_help.Caption = "scipy.signal.square(t, duty)  →  +1/-1 wave with variable duty cycle"
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)

        # =====================================================================
        # Time Parameters Section
        # =====================================================================
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 75
        sep1.Width = 470
        sep1.Height = 2
        sep1.Shape = "bsTopLine"

        lbl_time = vcl.TLabel(Form)
        lbl_time.Parent = Form
        lbl_time.Caption = "Time Parameters"
        lbl_time.Left = 10
        lbl_time.Top = 85
        lbl_time.Font.Style = {"fsBold"}
        labels.append(lbl_time)

        # t0 (start time)
        lbl_t0 = vcl.TLabel(Form)
        lbl_t0.Parent = Form
        lbl_t0.Caption = "tᵢ (start) [s]:"
        lbl_t0.Left = 20
        lbl_t0.Top = 113
        labels.append(lbl_t0)

        edt_t0 = vcl.TEdit(Form)
        edt_t0.Parent = Form
        edt_t0.Left = 120
        edt_t0.Top = 110
        edt_t0.Width = 80
        edt_t0.Text = "0"
        inputs["t0"] = edt_t0

        # tf (end time)
        lbl_tf = vcl.TLabel(Form)
        lbl_tf.Parent = Form
        lbl_tf.Caption = "tₑ (end) [s]:"
        lbl_tf.Left = 230
        lbl_tf.Top = 113
        labels.append(lbl_tf)

        edt_tf = vcl.TEdit(Form)
        edt_tf.Parent = Form
        edt_tf.Left = 320
        edt_tf.Top = 110
        edt_tf.Width = 80
        edt_tf.Text = "1"
        inputs["tf"] = edt_tf

        # fsample
        lbl_fs = vcl.TLabel(Form)
        lbl_fs.Parent = Form
        lbl_fs.Caption = "Sample Rate [Hz]:"
        lbl_fs.Left = 20
        lbl_fs.Top = 143
        labels.append(lbl_fs)

        edt_fs = vcl.TEdit(Form)
        edt_fs.Parent = Form
        edt_fs.Left = 140
        edt_fs.Top = 140
        edt_fs.Width = 80
        edt_fs.Text = "500"
        inputs["fs"] = edt_fs

        # Frequency
        lbl_freq = vcl.TLabel(Form)
        lbl_freq.Parent = Form
        lbl_freq.Caption = "Frequency [Hz]:"
        lbl_freq.Left = 250
        lbl_freq.Top = 143
        labels.append(lbl_freq)

        edt_freq = vcl.TEdit(Form)
        edt_freq.Parent = Form
        edt_freq.Left = 360
        edt_freq.Top = 140
        edt_freq.Width = 80
        edt_freq.Text = "5"
        inputs["freq"] = edt_freq

        # =====================================================================
        # Duty Cycle Section
        # =====================================================================
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 180
        sep2.Width = 470
        sep2.Height = 2
        sep2.Shape = "bsTopLine"

        lbl_duty = vcl.TLabel(Form)
        lbl_duty.Parent = Form
        lbl_duty.Caption = "Duty Cycle (0 to 1)"
        lbl_duty.Left = 10
        lbl_duty.Top = 190
        lbl_duty.Font.Style = {"fsBold"}
        labels.append(lbl_duty)

        # Duty source selector
        lbl_duty_src = vcl.TLabel(Form)
        lbl_duty_src.Parent = Form
        lbl_duty_src.Caption = "Source:"
        lbl_duty_src.Left = 20
        lbl_duty_src.Top = 218
        labels.append(lbl_duty_src)

        cmb_duty = vcl.TComboBox(Form)
        cmb_duty.Parent = Form
        cmb_duty.Left = 80
        cmb_duty.Top = 215
        cmb_duty.Width = 380
        cmb_duty.Style = 2  # csDropDownList
        for name, _, _ in duty_sources:
            cmb_duty.Items.Add(name)
        cmb_duty.ItemIndex = 0
        inputs["cmb_duty"] = cmb_duty

        # Constant duty value (shown only when "Constant value" selected)
        lbl_duty_val = vcl.TLabel(Form)
        lbl_duty_val.Parent = Form
        lbl_duty_val.Caption = "Value (0-1):"
        lbl_duty_val.Left = 20
        lbl_duty_val.Top = 253
        labels.append(lbl_duty_val)
        inputs["lbl_duty_val"] = lbl_duty_val

        edt_duty = vcl.TEdit(Form)
        edt_duty.Parent = Form
        edt_duty.Left = 100
        edt_duty.Top = 250
        edt_duty.Width = 80
        edt_duty.Text = "0.5"
        inputs["duty"] = edt_duty

        # Info label for series/function
        lbl_duty_info = vcl.TLabel(Form)
        lbl_duty_info.Parent = Form
        lbl_duty_info.Caption = "(Series/function will be normalized to 0-1 range if needed)"
        lbl_duty_info.Left = 200
        lbl_duty_info.Top = 253
        lbl_duty_info.Font.Color = 0x666666
        lbl_duty_info.Visible = False
        labels.append(lbl_duty_info)
        inputs["lbl_duty_info"] = lbl_duty_info

        def on_duty_source_change(Sender):
            idx = cmb_duty.ItemIndex
            is_constant = (idx == 0)
            edt_duty.Enabled = is_constant
            lbl_duty_val.Enabled = is_constant
            lbl_duty_info.Visible = not is_constant

        cmb_duty.OnChange = on_duty_source_change

        # =====================================================================
        # Appearance Section
        # =====================================================================
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 290
        sep3.Width = 470
        sep3.Height = 2
        sep3.Shape = "bsTopLine"

        lbl_appear = vcl.TLabel(Form)
        lbl_appear.Parent = Form
        lbl_appear.Caption = "Appearance"
        lbl_appear.Left = 10
        lbl_appear.Top = 300
        lbl_appear.Font.Style = {"fsBold"}
        labels.append(lbl_appear)

        # Color
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Line Color:"
        lbl_color.Left = 20
        lbl_color.Top = 328
        labels.append(lbl_color)

        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 100
        cb_color.Top = 325
        cb_color.Width = 110
        cb_color.Selected = 0x0000FF  # Red (BGR)
        inputs["color"] = cb_color

        # Thickness
        lbl_thick = vcl.TLabel(Form)
        lbl_thick.Parent = Form
        lbl_thick.Caption = "Line Width:"
        lbl_thick.Left = 240
        lbl_thick.Top = 328
        labels.append(lbl_thick)

        edt_thick = vcl.TEdit(Form)
        edt_thick.Parent = Form
        edt_thick.Left = 320
        edt_thick.Top = 325
        edt_thick.Width = 50
        edt_thick.Text = "1"
        inputs["thick"] = edt_thick

        # Checkbox to also plot duty signal
        chk_plot_duty = vcl.TCheckBox(Form)
        chk_plot_duty.Parent = Form
        chk_plot_duty.Caption = "Also plot duty cycle signal"
        chk_plot_duty.Left = 20
        chk_plot_duty.Top = 360
        chk_plot_duty.Width = 250
        chk_plot_duty.Checked = False
        inputs["chk_plot_duty"] = chk_plot_duty

        # =====================================================================
        # Buttons
        # =====================================================================
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10
        sep4.Top = 400
        sep4.Width = 470
        sep4.Height = 2
        sep4.Shape = "bsTopLine"

        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Generate"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 150
        btn_ok.Top = 420
        btn_ok.Width = 100
        btn_ok.Height = 30

        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 260
        btn_cancel.Top = 420
        btn_cancel.Width = 100
        btn_cancel.Height = 30

        # Show dialog
        if Form.ShowModal() == 1:
            try:
                # Read time parameters
                t0 = float(inputs["t0"].Text)
                tf = float(inputs["tf"].Text)
                fs = float(inputs["fs"].Text)
                freq = float(inputs["freq"].Text)
                thickness = int(inputs["thick"].Text)
                color_val = safe_color(inputs["color"].Selected)
                plot_duty = inputs["chk_plot_duty"].Checked

                # Validate
                if fs <= 0:
                    raise ValueError("Sample rate must be > 0")
                if tf <= t0:
                    raise ValueError("End time must be > Start time")
                if freq <= 0:
                    raise ValueError("Frequency must be > 0")

                # Generate time vector
                count = int((tf - t0) * fs) + 1
                t = np.linspace(t0, tf, count, endpoint=True)
                ts = 1.0 / fs  # Sampling period

                # Get duty cycle
                duty_idx = inputs["cmb_duty"].ItemIndex
                _, duty_type, duty_obj = duty_sources[duty_idx]

                if duty_type == "constant":
                    # Constant duty
                    duty_val = float(inputs["duty"].Text)
                    if duty_val < 0 or duty_val > 1:
                        raise ValueError("Duty cycle must be between 0 and 1")
                    duty = duty_val
                    duty_legend = f"duty={duty_val}"
                    duty_array = np.full(count, duty_val)
                
                elif duty_type == "series":
                    # Get series data
                    x_vals, y_vals = get_series_data(duty_obj)
                    if not x_vals or not y_vals:
                        raise ValueError("Could not read data from selected series")
                    
                    # Build duty array matching time vector length
                    duty_array = np.array(y_vals, dtype=float)
                    
                    # Extend if shorter than time vector
                    if len(duty_array) < count:
                        last_val = duty_array[-1]
                        duty_array = np.concatenate([
                            duty_array, 
                            np.full(count - len(duty_array), last_val)
                        ])
                    elif len(duty_array) > count:
                        duty_array = duty_array[:count]
                    
                    # Normalize to 0-1 range if needed
                    d_min, d_max = duty_array.min(), duty_array.max()
                    if d_min < 0 or d_max > 1:
                        duty_array = (duty_array - d_min) / (d_max - d_min) if d_max > d_min else np.full(count, 0.5)
                    
                    duty = duty_array
                    series_name = duty_obj.LegendText if duty_obj.LegendText else "Series"
                    duty_legend = f"duty={series_name}"
                
                elif duty_type == "function":
                    # Sample the function to get duty values
                    # Sample from 0 to n (length of time vector)
                    x_samp, y_samp, errors = sample_std_function(duty_obj, ts, 0, count - 1)
                    
                    if errors:
                        # Show warning but continue
                        pass
                    
                    # Build duty array
                    duty_array = np.array(y_samp, dtype=float)
                    
                    # Replace NaN with 0.5
                    duty_array = np.nan_to_num(duty_array, nan=0.5)
                    
                    # Extend if shorter
                    if len(duty_array) < count:
                        last_val = duty_array[-1] if len(duty_array) > 0 else 0.5
                        duty_array = np.concatenate([
                            duty_array,
                            np.full(count - len(duty_array), last_val)
                        ])
                    elif len(duty_array) > count:
                        duty_array = duty_array[:count]
                    
                    # Normalize to 0-1 range if needed
                    d_min, d_max = duty_array.min(), duty_array.max()
                    if d_min < 0 or d_max > 1:
                        duty_array = (duty_array - d_min) / (d_max - d_min) if d_max > d_min else np.full(count, 0.5)
                    
                    duty = duty_array
                    func_name = duty_obj.LegendText if duty_obj.LegendText else "Function"
                    duty_legend = f"duty={func_name}"
                
                else:
                    raise ValueError("Unknown duty source type")

                # Generate square wave
                # scipy.signal.square expects input in radians (period 2*pi)
                y = signal.square(2 * np.pi * freq * t, duty=duty)

                # Create output series
                points = [Point(t[i], y[i]) for i in range(len(t))]
                
                series = Graph.TPointSeries()
                series.PointType = Graph.ptCartesian
                series.Points = points
                series.LegendText = f"Square (f={freq}Hz, {duty_legend})"
                series.Size = 0
                series.Style = 0
                series.FillColor = color_val
                series.FrameColor = color_val
                series.LineSize = thickness
                series.LineColor = color_val
                series.ShowLabels = False
                Graph.FunctionList.append(series)

                # Optionally plot duty cycle
                if plot_duty and isinstance(duty, np.ndarray):
                    duty_points = [Point(t[i], duty_array[i]) for i in range(len(t))]
                    duty_series = Graph.TPointSeries()
                    duty_series.PointType = Graph.ptCartesian
                    duty_series.Points = duty_points
                    duty_series.LegendText = f"Duty ({duty_legend})"
                    duty_series.Size = 0
                    duty_series.Style = 0
                    duty_color = 0x00AA00  # Green
                    duty_series.FillColor = duty_color
                    duty_series.FrameColor = duty_color
                    duty_series.LineSize = 1    
                    duty_series.LineColor = duty_color
                    duty_series.LineStyle = 1
                    duty_series.ShowLabels = False
                    Graph.FunctionList.append(duty_series)

                Graph.Update()

            except Exception as e:
                vcl.MessageDlg(f"Parameter error: {str(e)}", 1, [0], 0)

    finally:
        Form.Free()


# Create action for custom menu
SquareWaveAction = Graph.CreateAction(
    Caption="Square Wave...",
    OnExecute=SquareWaveDialog,
    Hint="Generate square wave with variable duty cycle (scipy.signal.square)",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "SquareWave_sm.png")
)

# Add action to 'AWF Generators' submenu under 'Plugins -> Graphîa'
Graph.AddActionToMainMenu(SquareWaveAction, TopMenu="Plugins", SubMenus=["Graphîa", "AWF Generators"])  # type: ignore
