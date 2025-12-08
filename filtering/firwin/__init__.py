"""
FIR Filter - Plugin to design and apply FIR bandpass filters
Uses scipy.signal.firwin for kernel design and scipy.signal.filtfilt for zero-phase filtering.
"""

import Graph
import vcl  # type: ignore
import os

# Import common utilities
from common import (
    get_selected_point_series, show_error, show_info, 
    get_series_data, Point, safe_color, get_series_stats
)

# Import numpy and scipy
import numpy as np
from scipy.signal import firwin, filtfilt
from scipy.fft import fft

PluginName = "FIR Filter"
PluginVersion = "1.0"
PluginDescription = "Design and apply FIR bandpass filter using scipy.signal.firwin and filtfilt."


def fir_dialog(Action):
    """
    Shows a dialog to configure and apply FIR filter to the selected series.
    """
    # Get selected series
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "FIR Filter")
        return

    # Get current data
    x_vals, y_vals = get_series_data(series)
    
    if len(y_vals) < 10:
        show_info("The selected series must have at least 10 points.", "FIR Filter")
        return

    # Calculate stats for defaults
    stats = get_series_stats(series)
    n_points = stats['n_points']
    dx_avg = stats['dx_avg']
    
    # Estimate sample rate from average dx
    if dx_avg > 0:
        srate_default = 1.0 / dx_avg
    else:
        srate_default = 1.0
    
    # Default frequency range
    frange_low_default = 0.0
    frange_high_default = 0.25 * srate_default
    
    # Default kernel order: 5 * srate / frange[0], but avoid division by zero
    if frange_low_default > 0:
        order_default = int(5 * srate_default / frange_low_default)
    else:
        order_default = 101  # reasonable default
    
    # Force odd order
    if order_default % 2 == 0:
        order_default += 1
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "FIR Bandpass Filter (firwin)"
        Form.Width = 520
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
        help_panel.Width = 490
        help_panel.Height = 70
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0

        lbl_help_title = vcl.TLabel(help_panel)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "FIR Bandpass Filter Design (scipy.signal.firwin)"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        series_name = series.LegendText if series.LegendText else "(unnamed)"
        lbl_series = vcl.TLabel(help_panel)
        lbl_series.Parent = help_panel
        lbl_series.Caption = f"Series: {series_name}"
        lbl_series.Left = 10
        lbl_series.Top = 28
        lbl_series.Font.Color = 0x804000
        labels.append(lbl_series)
        
        lbl_info = vcl.TLabel(help_panel)
        lbl_info.Parent = help_panel
        lbl_info.Caption = f"n = {n_points} points  |  Est. srate ≈ {srate_default:.4g} Hz  |  Nyquist = {srate_default/2:.4g} Hz"
        lbl_info.Left = 10
        lbl_info.Top = 48
        lbl_info.Font.Color = 0x804000
        labels.append(lbl_info)

        # =====================================================================
        # Parameters Section
        # =====================================================================
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 90
        sep1.Width = 490
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        lbl_params = vcl.TLabel(Form)
        lbl_params.Parent = Form
        lbl_params.Caption = "Filter Parameters"
        lbl_params.Left = 10
        lbl_params.Top = 100
        lbl_params.Font.Style = {"fsBold"}
        labels.append(lbl_params)
        
        # Panel for parameters
        pnl_params = vcl.TPanel(Form)
        pnl_params.Parent = Form
        pnl_params.Left = 10
        pnl_params.Top = 123
        pnl_params.Width = 490
        pnl_params.Height = 140
        pnl_params.BevelOuter = "bvLowered"
        
        # Sample rate
        lbl_srate = vcl.TLabel(Form)
        lbl_srate.Parent = pnl_params
        lbl_srate.Caption = "Sample rate (fs):"
        lbl_srate.Left = 15
        lbl_srate.Top = 15
        labels.append(lbl_srate)
        
        edt_srate = vcl.TEdit(Form)
        edt_srate.Parent = pnl_params
        edt_srate.Left = 160
        edt_srate.Top = 12
        edt_srate.Width = 100
        edt_srate.Text = f"{srate_default:.6g}"
        
        lbl_srate_unit = vcl.TLabel(Form)
        lbl_srate_unit.Parent = pnl_params
        lbl_srate_unit.Caption = "Hz"
        lbl_srate_unit.Left = 270
        lbl_srate_unit.Top = 15
        lbl_srate_unit.Font.Color = 0x666666
        labels.append(lbl_srate_unit)
        
        # Frequency range lower
        lbl_flow = vcl.TLabel(Form)
        lbl_flow.Parent = pnl_params
        lbl_flow.Caption = "F-range lower (f1):"
        lbl_flow.Left = 15
        lbl_flow.Top = 45
        labels.append(lbl_flow)
        
        edt_flow = vcl.TEdit(Form)
        edt_flow.Parent = pnl_params
        edt_flow.Left = 160
        edt_flow.Top = 42
        edt_flow.Width = 100
        edt_flow.Text = f"{frange_low_default:.6g}"
        
        lbl_flow_unit = vcl.TLabel(Form)
        lbl_flow_unit.Parent = pnl_params
        lbl_flow_unit.Caption = "Hz (0 = lowpass)"
        lbl_flow_unit.Left = 270
        lbl_flow_unit.Top = 45
        lbl_flow_unit.Font.Color = 0x666666
        labels.append(lbl_flow_unit)
        
        # Frequency range upper
        lbl_fhigh = vcl.TLabel(Form)
        lbl_fhigh.Parent = pnl_params
        lbl_fhigh.Caption = "F-range upper (f2):"
        lbl_fhigh.Left = 15
        lbl_fhigh.Top = 75
        labels.append(lbl_fhigh)
        
        edt_fhigh = vcl.TEdit(Form)
        edt_fhigh.Parent = pnl_params
        edt_fhigh.Left = 160
        edt_fhigh.Top = 72
        edt_fhigh.Width = 100
        edt_fhigh.Text = f"{frange_high_default:.6g}"
        
        lbl_fhigh_unit = vcl.TLabel(Form)
        lbl_fhigh_unit.Parent = pnl_params
        lbl_fhigh_unit.Caption = "Hz (< Nyquist)"
        lbl_fhigh_unit.Left = 270
        lbl_fhigh_unit.Top = 75
        lbl_fhigh_unit.Font.Color = 0x666666
        labels.append(lbl_fhigh_unit)
        
        # Kernel order
        lbl_order = vcl.TLabel(Form)
        lbl_order.Parent = pnl_params
        lbl_order.Caption = "Kernel order:"
        lbl_order.Left = 15
        lbl_order.Top = 105
        labels.append(lbl_order)
        
        edt_order = vcl.TEdit(Form)
        edt_order.Parent = pnl_params
        edt_order.Left = 160
        edt_order.Top = 102
        edt_order.Width = 100
        edt_order.Text = str(order_default)
        
        lbl_order_info = vcl.TLabel(Form)
        lbl_order_info.Parent = pnl_params
        lbl_order_info.Caption = "(odd, higher = sharper)"
        lbl_order_info.Left = 270
        lbl_order_info.Top = 105
        lbl_order_info.Font.Color = 0x666666
        labels.append(lbl_order_info)

        # =====================================================================
        # Output Section
        # =====================================================================
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 273
        sep2.Width = 490
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output Options"
        lbl_output.Left = 10
        lbl_output.Top = 283
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Checkboxes for what to plot
        chk_kernel = vcl.TCheckBox(Form)
        chk_kernel.Parent = Form
        chk_kernel.Caption = "Plot filter kernel"
        chk_kernel.Left = 20
        chk_kernel.Top = 310
        chk_kernel.Checked = True
        
        chk_spectrum = vcl.TCheckBox(Form)
        chk_spectrum.Parent = Form
        chk_spectrum.Caption = "Plot kernel spectrum (actual & ideal)"
        chk_spectrum.Left = 20
        chk_spectrum.Top = 335
        chk_spectrum.Checked = True
        
        chk_filtered = vcl.TCheckBox(Form)
        chk_filtered.Parent = Form
        chk_filtered.Caption = "Plot filtered signal"
        chk_filtered.Left = 20
        chk_filtered.Top = 360
        chk_filtered.Checked = True
        
        # Color selector
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Filtered signal color:"
        lbl_color.Left = 250
        lbl_color.Top = 360
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 380
        cb_color.Top = 357
        cb_color.Width = 100
        cb_color.Selected = 0x00AA00  # Green by default

        # =====================================================================
        # Buttons
        # =====================================================================
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 395
        sep3.Width = 490
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        btn_compute = vcl.TButton(Form)
        btn_compute.Parent = Form
        btn_compute.Caption = "Apply Filter"
        btn_compute.Left = 160
        btn_compute.Top = 410
        btn_compute.Width = 110
        btn_compute.Height = 30
        btn_compute.Default = True
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 280
        btn_cancel.Top = 410
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        def on_compute(Sender):
            try:
                # Parse sample rate
                try:
                    srate = float(edt_srate.Text)
                    if srate <= 0:
                        raise ValueError("Sample rate must be > 0")
                except ValueError as e:
                    show_error(f"Invalid sample rate: {e}", "FIR Filter")
                    return
                
                nyquist = srate / 2.0
                
                # Parse frequency range
                try:
                    f_low = float(edt_flow.Text)
                    if f_low < 0:
                        raise ValueError("Lower frequency must be >= 0")
                except ValueError as e:
                    show_error(f"Invalid lower frequency: {e}", "FIR Filter")
                    return
                
                try:
                    f_high = float(edt_fhigh.Text)
                    if f_high <= 0:
                        raise ValueError("Upper frequency must be > 0")
                    if f_high >= nyquist:
                        raise ValueError(f"Upper frequency must be < Nyquist ({nyquist:.4g} Hz)")
                except ValueError as e:
                    show_error(f"Invalid upper frequency: {e}", "FIR Filter")
                    return
                
                if f_low >= f_high:
                    show_error("Lower frequency must be < upper frequency", "FIR Filter")
                    return
                
                # Parse order
                try:
                    order = int(edt_order.Text)
                    if order < 3:
                        raise ValueError("Order must be >= 3")
                except ValueError as e:
                    show_error(f"Invalid kernel order: {e}", "FIR Filter")
                    return
                
                # Force odd order
                if order % 2 == 0:
                    order += 1
                
                # Determine filter type and frequency specification
                if f_low == 0:
                    # Lowpass filter
                    frange = f_high
                    pass_zero = True
                else:
                    # Bandpass filter
                    frange = [f_low, f_high]
                    pass_zero = False
                
                # Design filter kernel
                filtkern = firwin(order, frange, fs=srate, pass_zero=pass_zero)
                
                # =========================================================
                # Plot 1: Filter kernel
                # =========================================================
                if chk_kernel.Checked:
                    kernel_x = list(range(order))
                    kernel_points = [Point(float(i), float(filtkern[i])) for i in range(order)]
                    
                    kernel_series = Graph.TPointSeries()
                    kernel_series.Points = kernel_points
                    kernel_series.LegendText = f"FIR Kernel (order={order})"
                    kernel_series.Size = 2
                    kernel_series.Style = 0
                    kernel_series.LineSize = 1
                    kernel_series.ShowLabels = False
                    kernel_series.FillColor = 0xFF0000  # Blue
                    kernel_series.FrameColor = 0xFF0000
                    kernel_series.LineColor = 0xFF0000
                    
                    Graph.FunctionList.append(kernel_series)
                
                # =========================================================
                # Plot 2: Kernel amplitude spectrum (actual)
                # =========================================================
                if chk_spectrum.Checked:
                    # Compute the power spectrum of the filter kernel
                    filtpow = np.abs(fft(filtkern)) ** 2
                    
                    # Compute the frequencies vector and remove negative frequencies
                    hz = np.linspace(0, srate / 2, int(np.floor(len(filtkern) / 2) + 1))
                    filtpow = filtpow[0:len(hz)]
                    
                    # Normalize for display
                    if np.max(filtpow) > 0:
                        filtpow_norm = filtpow / np.max(filtpow)
                    else:
                        filtpow_norm = filtpow
                    
                    spectrum_points = [Point(float(hz[i]), float(filtpow_norm[i])) for i in range(len(hz))]
                    
                    spectrum_series = Graph.TPointSeries()
                    spectrum_series.Points = spectrum_points
                    spectrum_series.LegendText = "Kernel actual spectrum"
                    spectrum_series.Size = 0
                    spectrum_series.Style = 0
                    spectrum_series.LineSize = 2
                    spectrum_series.ShowLabels = False
                    spectrum_series.FillColor = 0x00AAFF  # Orange
                    spectrum_series.FrameColor = 0x00AAFF
                    spectrum_series.LineColor = 0x00AAFF
                    
                    Graph.FunctionList.append(spectrum_series)
                    
                    # =========================================================
                    # Plot 3: Ideal kernel spectrum
                    # =========================================================
                    if f_low == 0:
                        # Lowpass ideal
                        ideal_x = [0, f_high, f_high, nyquist]
                        ideal_y = [1, 1, 0, 0]
                    else:
                        # Bandpass ideal
                        ideal_x = [0, f_low, f_low, f_high, f_high, nyquist]
                        ideal_y = [0, 0, 1, 1, 0, 0]
                    
                    ideal_points = [Point(float(ideal_x[i]), float(ideal_y[i])) for i in range(len(ideal_x))]
                    
                    ideal_series = Graph.TPointSeries()
                    ideal_series.Points = ideal_points
                    ideal_series.LegendText = "Kernel ideal spectrum"
                    ideal_series.Size = 0
                    ideal_series.Style = 0
                    ideal_series.LineSize = 2
                    ideal_series.ShowLabels = False
                    ideal_series.FillColor = 0x0000FF  # Red
                    ideal_series.FrameColor = 0x0000FF
                    ideal_series.LineColor = 0x0000FF
                    
                    Graph.FunctionList.append(ideal_series)
                
                # =========================================================
                # Plot 4: Apply filter and plot filtered signal
                # =========================================================
                if chk_filtered.Checked:
                    signal = np.array(y_vals)
                    
                    # Apply zero-phase filtering
                    y_filt = filtfilt(filtkern, 1, signal)
                    
                    # Create filtered signal series
                    filt_points = [Point(float(x_vals[i]), float(y_filt[i])) for i in range(len(y_filt))]
                    
                    filt_series = Graph.TPointSeries()
                    filt_series.Points = filt_points
                    
                    original_legend = series.LegendText if series.LegendText else "Signal"
                    if f_low == 0:
                        filt_series.LegendText = f"{original_legend} [LP {f_high:.2g} Hz]"
                    else:
                        filt_series.LegendText = f"{original_legend} [BP {f_low:.2g}-{f_high:.2g} Hz]"
                    
                    filt_series.Size = 0
                    filt_series.Style = 0
                    filt_series.LineSize = 2
                    filt_series.ShowLabels = False
                    
                    color_val = safe_color(cb_color.Selected)
                    filt_series.FillColor = color_val
                    filt_series.FrameColor = color_val
                    filt_series.LineColor = color_val
                    
                    Graph.FunctionList.append(filt_series)
                
                Graph.Update()
                
                show_info(
                    f"FIR Filter applied successfully:\n"
                    f"• Order: {order}\n"
                    f"• Passband: {f_low:.4g} - {f_high:.4g} Hz\n"
                    f"• Sample rate: {srate:.4g} Hz",
                    "FIR Filter"
                )
                
                Form.ModalResult = 1  # mrOk
                
            except Exception as e:
                show_error(f"Error applying filter: {str(e)}", "FIR Filter")
        
        btn_compute.OnClick = on_compute
        
        # Show dialog
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="FIR Bandpass Filter...", 
    OnExecute=fir_dialog, 
    Hint="Design and apply FIR bandpass filter using firwin",
    IconFile=None  # No icon for now
)

# Add to Plugins -> Filtering menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Filtering"])
