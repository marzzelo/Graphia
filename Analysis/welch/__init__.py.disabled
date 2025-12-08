"""
Welch PSD - Plugin to compute Power Spectral Density using Welch's method
Uses scipy.signal.welch to estimate power spectral density.
"""

import Graph
import vcl  # type: ignore
import os

# Import common utilities
from common import (
    setup_venv, get_selected_point_series, show_error, show_info, 
    get_series_data, Point, safe_color, get_series_stats
)

# Import numpy and scipy
import numpy as np
from scipy.signal import welch

PluginName = "Welch PSD"
PluginVersion = "1.0"
PluginDescription = "Compute Power Spectral Density using Welch's method."

# Available window functions
WINDOW_TYPES = [
    ("Hann", "hann"),
    ("Hamming", "hamming"),
    ("Blackman", "blackman"),
    ("Blackman-Harris", "blackmanharris"),
    ("Flat Top", "flattop"),
    ("Rectangular (boxcar)", "boxcar"),
    ("Bartlett", "bartlett"),
    ("Kaiser (β=8)", ("kaiser", 8)),
]

# Detrend options
DETREND_OPTIONS = [
    ("Constant (subtract mean)", "constant"),
    ("Linear (subtract trend)", "linear"),
    ("None (no detrend)", False),
]

# Scaling options
SCALING_OPTIONS = [
    ("Density (V²/Hz)", "density"),
    ("Spectrum (V²)", "spectrum"),
]

# Average options
AVERAGE_OPTIONS = [
    ("Mean", "mean"),
    ("Median", "median"),
]


def welch_dialog(Action):
    """
    Shows a dialog to configure and compute PSD using Welch's method.
    """
    # Get selected series
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "Welch PSD")
        return

    # Get current data
    x_vals, y_vals = get_series_data(series)
    
    if len(y_vals) < 4:
        show_info("The selected series must have at least 4 points.", "Welch PSD")
        return

    # Calculate stats for info
    stats = get_series_stats(series)
    n_points = stats['n_points']
    x_min = stats['x_min']
    x_max = stats['x_max']
    dx_avg = stats['dx_avg']
    
    # Estimate sample rate from average dx
    if dx_avg > 0:
        srate_estimated = 1.0 / dx_avg
    else:
        srate_estimated = 1.0
    
    # Default nperseg: 256 or n_points//4, whichever is smaller
    nperseg_default = min(256, n_points // 4) if n_points >= 16 else n_points // 2
    nperseg_default = max(nperseg_default, 4)  # At least 4
    
    # Default noverlap: 50% of nperseg
    noverlap_default = nperseg_default // 2
    
    # Default max frequency = Nyquist (fs/2)
    f_max_default = srate_estimated / 2.0
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Power Spectral Density (Welch)"
        Form.Width = 520
        Form.Height = 550
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
        lbl_help_title.Caption = "Power Spectral Density - Welch's Method"
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
        lbl_info.Caption = f"N = {n_points} points  |  X ∈ [{x_min:.4g}, {x_max:.4g}]  |  Δx ≈ {dx_avg:.6g}  |  fs ≈ {srate_estimated:.4g}"
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
        lbl_params.Caption = "Welch Parameters"
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
        pnl_params.Height = 250
        pnl_params.BevelOuter = "bvLowered"
        
        row_height = 30
        label_left = 15
        input_left = 140
        info_left = 280
        current_top = 12
        
        # Sample rate
        lbl_srate = vcl.TLabel(Form)
        lbl_srate.Parent = pnl_params
        lbl_srate.Caption = "Sample rate (fs):"
        lbl_srate.Left = label_left
        lbl_srate.Top = current_top + 3
        labels.append(lbl_srate)
        
        edt_srate = vcl.TEdit(Form)
        edt_srate.Parent = pnl_params
        edt_srate.Left = input_left
        edt_srate.Top = current_top
        edt_srate.Width = 100
        edt_srate.Text = f"{srate_estimated:.6g}"
        
        lbl_srate_info = vcl.TLabel(Form)
        lbl_srate_info.Parent = pnl_params
        lbl_srate_info.Caption = "(computed from average Δx)"
        lbl_srate_info.Left = info_left
        lbl_srate_info.Top = current_top + 3
        lbl_srate_info.Font.Color = 0x666666
        labels.append(lbl_srate_info)
        
        current_top += row_height
        
        # nperseg
        lbl_nperseg = vcl.TLabel(Form)
        lbl_nperseg.Parent = pnl_params
        lbl_nperseg.Caption = "nperseg:"
        lbl_nperseg.Left = label_left
        lbl_nperseg.Top = current_top + 3
        labels.append(lbl_nperseg)
        
        edt_nperseg = vcl.TEdit(Form)
        edt_nperseg.Parent = pnl_params
        edt_nperseg.Left = input_left
        edt_nperseg.Top = current_top
        edt_nperseg.Width = 100
        edt_nperseg.Text = str(nperseg_default)
        
        lbl_nperseg_info = vcl.TLabel(Form)
        lbl_nperseg_info.Parent = pnl_params
        lbl_nperseg_info.Caption = "(length of each segment)"
        lbl_nperseg_info.Left = info_left
        lbl_nperseg_info.Top = current_top + 3
        lbl_nperseg_info.Font.Color = 0x666666
        labels.append(lbl_nperseg_info)
        
        current_top += row_height
        
        # noverlap
        lbl_noverlap = vcl.TLabel(Form)
        lbl_noverlap.Parent = pnl_params
        lbl_noverlap.Caption = "noverlap:"
        lbl_noverlap.Left = label_left
        lbl_noverlap.Top = current_top + 3
        labels.append(lbl_noverlap)
        
        edt_noverlap = vcl.TEdit(Form)
        edt_noverlap.Parent = pnl_params
        edt_noverlap.Left = input_left
        edt_noverlap.Top = current_top
        edt_noverlap.Width = 100
        edt_noverlap.Text = str(noverlap_default)
        
        lbl_noverlap_info = vcl.TLabel(Form)
        lbl_noverlap_info.Parent = pnl_params
        lbl_noverlap_info.Caption = "(samples of overlap, default=50%)"
        lbl_noverlap_info.Left = info_left
        lbl_noverlap_info.Top = current_top + 3
        lbl_noverlap_info.Font.Color = 0x666666
        labels.append(lbl_noverlap_info)
        
        current_top += row_height
        
        # Window function
        lbl_window = vcl.TLabel(Form)
        lbl_window.Parent = pnl_params
        lbl_window.Caption = "Window:"
        lbl_window.Left = label_left
        lbl_window.Top = current_top + 3
        labels.append(lbl_window)
        
        cmb_window = vcl.TComboBox(Form)
        cmb_window.Parent = pnl_params
        cmb_window.Left = input_left
        cmb_window.Top = current_top
        cmb_window.Width = 180
        cmb_window.Style = "csDropDownList"
        for name, _ in WINDOW_TYPES:
            cmb_window.Items.Add(name)
        cmb_window.ItemIndex = 0  # Default: Hann
        
        current_top += row_height
        
        # Detrend
        lbl_detrend = vcl.TLabel(Form)
        lbl_detrend.Parent = pnl_params
        lbl_detrend.Caption = "Detrend:"
        lbl_detrend.Left = label_left
        lbl_detrend.Top = current_top + 3
        labels.append(lbl_detrend)
        
        cmb_detrend = vcl.TComboBox(Form)
        cmb_detrend.Parent = pnl_params
        cmb_detrend.Left = input_left
        cmb_detrend.Top = current_top
        cmb_detrend.Width = 220
        cmb_detrend.Style = "csDropDownList"
        for name, _ in DETREND_OPTIONS:
            cmb_detrend.Items.Add(name)
        cmb_detrend.ItemIndex = 0  # Default: constant
        
        current_top += row_height
        
        # Scaling
        lbl_scaling = vcl.TLabel(Form)
        lbl_scaling.Parent = pnl_params
        lbl_scaling.Caption = "Scaling:"
        lbl_scaling.Left = label_left
        lbl_scaling.Top = current_top + 3
        labels.append(lbl_scaling)
        
        cmb_scaling = vcl.TComboBox(Form)
        cmb_scaling.Parent = pnl_params
        cmb_scaling.Left = input_left
        cmb_scaling.Top = current_top
        cmb_scaling.Width = 180
        cmb_scaling.Style = "csDropDownList"
        for name, _ in SCALING_OPTIONS:
            cmb_scaling.Items.Add(name)
        cmb_scaling.ItemIndex = 0  # Default: density
        
        current_top += row_height
        
        # Average
        lbl_average = vcl.TLabel(Form)
        lbl_average.Parent = pnl_params
        lbl_average.Caption = "Average:"
        lbl_average.Left = label_left
        lbl_average.Top = current_top + 3
        labels.append(lbl_average)
        
        cmb_average = vcl.TComboBox(Form)
        cmb_average.Parent = pnl_params
        cmb_average.Left = input_left
        cmb_average.Top = current_top
        cmb_average.Width = 180
        cmb_average.Style = "csDropDownList"
        for name, _ in AVERAGE_OPTIONS:
            cmb_average.Items.Add(name)
        cmb_average.ItemIndex = 0  # Default: mean
        
        current_top += row_height
        
        # Max frequency cutoff
        lbl_fmax = vcl.TLabel(Form)
        lbl_fmax.Parent = pnl_params
        lbl_fmax.Caption = "Max frequency:"
        lbl_fmax.Left = label_left
        lbl_fmax.Top = current_top + 3
        labels.append(lbl_fmax)
        
        edt_fmax = vcl.TEdit(Form)
        edt_fmax.Parent = pnl_params
        edt_fmax.Left = input_left
        edt_fmax.Top = current_top
        edt_fmax.Width = 100
        edt_fmax.Text = f"{f_max_default:.6g}"
        
        lbl_fmax_info = vcl.TLabel(Form)
        lbl_fmax_info.Parent = pnl_params
        lbl_fmax_info.Caption = f"(cutoff output, Nyquist = {f_max_default:.4g})"
        lbl_fmax_info.Left = info_left
        lbl_fmax_info.Top = current_top + 3
        lbl_fmax_info.Font.Color = 0x666666
        labels.append(lbl_fmax_info)

        # =====================================================================
        # Output Section
        # =====================================================================
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 383
        sep2.Width = 490
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output"
        lbl_output.Left = 10
        lbl_output.Top = 393
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Color selector
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Spectrum color:"
        lbl_color.Left = 20
        lbl_color.Top = 420
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 140
        cb_color.Top = 417
        cb_color.Width = 100
        cb_color.Selected = 0xAA0000  # Blue by default
        
        # =====================================================================
        # Buttons
        # =====================================================================
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 460
        sep3.Width = 490
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        btn_compute = vcl.TButton(Form)
        btn_compute.Parent = Form
        btn_compute.Caption = "Compute PSD"
        btn_compute.Left = 160
        btn_compute.Top = 478
        btn_compute.Width = 110
        btn_compute.Height = 30
        btn_compute.Default = True
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 280
        btn_cancel.Top = 478
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
                    show_error(f"Invalid sample rate: {e}", "Welch PSD")
                    return
                
                # Parse nperseg
                try:
                    nperseg = int(edt_nperseg.Text)
                    if nperseg < 2:
                        raise ValueError("nperseg must be >= 2")
                except ValueError as e:
                    show_error(f"Invalid nperseg: {e}", "Welch PSD")
                    return
                
                # Parse noverlap
                try:
                    noverlap = int(edt_noverlap.Text)
                    if noverlap < 0:
                        raise ValueError("noverlap must be >= 0")
                    if noverlap >= nperseg:
                        raise ValueError("noverlap must be < nperseg")
                except ValueError as e:
                    show_error(f"Invalid noverlap: {e}", "Welch PSD")
                    return
                
                # Parse max frequency cutoff
                try:
                    f_max = float(edt_fmax.Text)
                    if f_max <= 0:
                        raise ValueError("Max frequency must be > 0")
                except ValueError as e:
                    show_error(f"Invalid max frequency: {e}", "Welch PSD")
                    return
                
                # Get options from combo boxes
                _, window_param = WINDOW_TYPES[cmb_window.ItemIndex]
                _, detrend_param = DETREND_OPTIONS[cmb_detrend.ItemIndex]
                _, scaling_param = SCALING_OPTIONS[cmb_scaling.ItemIndex]
                _, average_param = AVERAGE_OPTIONS[cmb_average.ItemIndex]
                
                # Get signal data
                signal = np.array(y_vals)
                
                # Check if signal is long enough for nperseg
                if len(signal) < nperseg:
                    show_error(
                        f"Signal has {len(signal)} points, but nperseg={nperseg}.\n"
                        f"Reduce nperseg to a value less than {len(signal)}.",
                        "Welch PSD"
                    )
                    return
                
                # Compute Welch PSD
                f, psd = welch(
                    signal,
                    fs=srate,
                    window=window_param,
                    nperseg=nperseg,
                    noverlap=noverlap,
                    detrend=detrend_param,
                    scaling=scaling_param,
                    average=average_param,
                    return_onesided=True
                )
                
                # Cutoff: filter to max frequency
                mask = f <= f_max
                f_filtered = f[mask]
                psd_filtered = psd[mask]
                
                # Create points for the spectrum
                points = [Point(float(freq), float(p)) for freq, p in zip(f_filtered, psd_filtered)]
                
                # Create series
                psd_series = Graph.TPointSeries()
                psd_series.Points = points
                
                # Legend
                original_legend = series.LegendText if series.LegendText else "Series"
                scaling_short = "PSD" if scaling_param == "density" else "PS"
                psd_series.LegendText = f"{original_legend} [{scaling_short} Welch, nperseg={nperseg}]"
                
                # Style - line only, no points
                psd_series.Size = 0
                psd_series.Style = 0
                psd_series.LineSize = 2
                psd_series.ShowLabels = False
                
                # Color
                color_val = safe_color(cb_color.Selected)
                psd_series.FillColor = color_val
                psd_series.FrameColor = color_val
                psd_series.LineColor = color_val
                
                # Add to graph
                Graph.FunctionList.append(psd_series)
                Graph.Update()
                
                # Calculate resolution
                delta_f = srate / nperseg
                n_segments = (len(signal) - noverlap) // (nperseg - noverlap)
                
                units = "V²/Hz" if scaling_param == "density" else "V²"
                
                show_info(
                    f"Welch PSD computed:\n"
                    f"• nperseg = {nperseg}, noverlap = {noverlap}\n"
                    f"• Averaged segments: ~{n_segments}\n"
                    f"• Frequency resolution: Δf = {delta_f:.6g} Hz\n"
                    f"• Output range: 0 to {f_filtered[-1]:.4g} Hz\n"
                    f"• Units: {units}",
                    "Welch PSD"
                )
                
                Form.ModalResult = 1  # mrOk
                
            except Exception as e:
                show_error(f"Error computing PSD: {str(e)}", "Welch PSD")
        
        btn_compute.OnClick = on_compute
        
        # Show dialog
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="Welch PSD...", 
    OnExecute=welch_dialog, 
    Hint="Compute Power Spectral Density using Welch's method",
    IconFile=os.path.join(os.path.dirname(__file__), "welch_sm.png")
)

# Add to Plugins -> Analysis menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Analysis"])
