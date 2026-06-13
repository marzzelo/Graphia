"""
IFFT - Plugin para calcular la Transformada Inversa de Fourier
Usa scipy.fft.irfft para reconstruir señales en el dominio del tiempo
desde su representación en frecuencia (espectro de amplitud complejo).
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
from scipy.fft import irfft

PluginName = "IFFT"
PluginVersion = "1.0"
PluginDescription = "Compute inverse FFT to reconstruct time-domain signal (scipy.fft.irfft)."


def ifft_dialog(Action):
    """
    Shows a dialog to configure and compute IFFT from the selected series.
    The input series is expected to be the output of rfft (frequency domain).
    """
    # Get selected series
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "IFFT")
        return

    # Get current data
    x_vals, y_vals = get_series_data(series)
    
    if len(y_vals) < 2:
        show_info("The selected series must have at least 2 points.", "IFFT")
        return

    # Calculate stats for info
    stats = get_series_stats(series)
    n_points = stats['n_points']
    x_min = stats['x_min']
    x_max = stats['x_max']
    dx_avg = stats['dx_avg']
    
    # For IFFT: input has m points, default output length is 2*(m-1)
    m = n_points
    n_default = 2 * (m - 1)
    
    # Estimate frequency resolution from X axis (which should be in Hz)
    # df = fs/n, so fs = n * df
    if dx_avg > 0:
        df_estimated = dx_avg  # X axis should be frequency
        fs_estimated = n_default * df_estimated
    else:
        df_estimated = 1.0
        fs_estimated = n_default
    
    # Time step will be 1/fs
    dt_estimated = 1.0 / fs_estimated if fs_estimated > 0 else 1.0
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "IFFT - Inverse Fast Fourier Transform"
        Form.Width = 480
        Form.Height = 430
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
        help_panel.Width = 450
        help_panel.Height = 70
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0

        lbl_help_title = vcl.TLabel(help_panel)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Inverse Fast Fourier Transform (IRFFT)"
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
        lbl_info.Caption = f"m = {n_points} points  |  f ∈ [{x_min:.4g}, {x_max:.4g}]  |  Δf ≈ {df_estimated:.6g} Hz"
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
        sep1.Width = 450
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        lbl_params = vcl.TLabel(Form)
        lbl_params.Parent = Form
        lbl_params.Caption = "IFFT Parameters"
        lbl_params.Left = 10
        lbl_params.Top = 100
        lbl_params.Font.Style = {"fsBold"}
        labels.append(lbl_params)
        
        # Panel for parameters
        pnl_params = vcl.TPanel(Form)
        pnl_params.Parent = Form
        pnl_params.Left = 10
        pnl_params.Top = 123
        pnl_params.Width = 450
        pnl_params.Height = 130
        pnl_params.BevelOuter = "bvLowered"
        
        # n (output length)
        lbl_n = vcl.TLabel(Form)
        lbl_n.Parent = pnl_params
        lbl_n.Caption = "n (output length):"
        lbl_n.Left = 15
        lbl_n.Top = 15
        labels.append(lbl_n)
        
        edt_n = vcl.TEdit(Form)
        edt_n.Parent = pnl_params
        edt_n.Left = 140
        edt_n.Top = 12
        edt_n.Width = 80
        edt_n.Text = str(n_default)
        
        lbl_n_info = vcl.TLabel(Form)
        lbl_n_info.Parent = pnl_params
        lbl_n_info.Caption = f"(default = 2*(m-1) = {n_default})"
        lbl_n_info.Left = 230
        lbl_n_info.Top = 15
        lbl_n_info.Font.Color = 0x666666
        labels.append(lbl_n_info)
        
        # Sample rate (fs)
        lbl_srate = vcl.TLabel(Form)
        lbl_srate.Parent = pnl_params
        lbl_srate.Caption = "Sample rate (fs):"
        lbl_srate.Left = 15
        lbl_srate.Top = 45
        labels.append(lbl_srate)
        
        edt_srate = vcl.TEdit(Form)
        edt_srate.Parent = pnl_params
        edt_srate.Left = 140
        edt_srate.Top = 42
        edt_srate.Width = 80
        edt_srate.Text = f"{fs_estimated:.6g}"
        
        lbl_srate_info = vcl.TLabel(Form)
        lbl_srate_info.Parent = pnl_params
        lbl_srate_info.Caption = "(to generate time axis: dt = 1/fs)"
        lbl_srate_info.Left = 230
        lbl_srate_info.Top = 45
        lbl_srate_info.Font.Color = 0x666666
        labels.append(lbl_srate_info)
        
        # Time offset (t0)
        lbl_t0 = vcl.TLabel(Form)
        lbl_t0.Parent = pnl_params
        lbl_t0.Caption = "Start time (t₀):"
        lbl_t0.Left = 15
        lbl_t0.Top = 75
        labels.append(lbl_t0)
        
        edt_t0 = vcl.TEdit(Form)
        edt_t0.Parent = pnl_params
        edt_t0.Left = 140
        edt_t0.Top = 72
        edt_t0.Width = 80
        edt_t0.Text = "0"
        
        lbl_t0_info = vcl.TLabel(Form)
        lbl_t0_info.Parent = pnl_params
        lbl_t0_info.Caption = "(time axis offset)"
        lbl_t0_info.Left = 230
        lbl_t0_info.Top = 75
        lbl_t0_info.Font.Color = 0x666666
        labels.append(lbl_t0_info)
        
        # Output info
        lbl_output_info = vcl.TLabel(Form)
        lbl_output_info.Parent = pnl_params
        lbl_output_info.Caption = f"Est. Δt: {dt_estimated:.6g}  |  Duration: {n_default * dt_estimated:.6g}"
        lbl_output_info.Left = 15
        lbl_output_info.Top = 105
        lbl_output_info.Font.Color = 0x008800
        labels.append(lbl_output_info)

        # =====================================================================
        # Output Section
        # =====================================================================
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 263
        sep2.Width = 450
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output"
        lbl_output.Left = 10
        lbl_output.Top = 273
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Color selector
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Signal color:"
        lbl_color.Left = 20
        lbl_color.Top = 300
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 140
        cb_color.Top = 297
        cb_color.Width = 100
        cb_color.Selected = 0x0000AA  # Red by default (different from FFT)
        
        # Phase reconstruction option
        lbl_phase = vcl.TLabel(Form)
        lbl_phase.Parent = Form
        lbl_phase.Caption = "Assumed phase:"
        lbl_phase.Left = 250
        lbl_phase.Top = 300
        labels.append(lbl_phase)
        
        cb_phase = vcl.TComboBox(Form)
        cb_phase.Parent = Form
        cb_phase.Left = 330
        cb_phase.Top = 297
        cb_phase.Width = 110
        cb_phase.Style = "csDropDownList"
        cb_phase.Items.Add("0° (Cosines)")
        cb_phase.Items.Add("-90° (Sines)")
        cb_phase.Items.Add("180° (-Cosines)")
        cb_phase.Items.Add("90° (-Sines)")
        cb_phase.ItemIndex = 1  # Default to Sines
        
        # =====================================================================
        # Buttons
        # =====================================================================
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 335
        sep3.Width = 450
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        btn_compute = vcl.TButton(Form)
        btn_compute.Parent = Form
        btn_compute.Caption = "Compute IFFT"
        btn_compute.Left = 140
        btn_compute.Top = 350
        btn_compute.Width = 110
        btn_compute.Height = 30
        btn_compute.Default = True
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 260
        btn_cancel.Top = 350
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        def on_compute(Sender):
            try:
                # Parse n (output length)
                try:
                    n_output = int(edt_n.Text)
                    if n_output < 1:
                        raise ValueError("n must be >= 1")
                except ValueError as e:
                    show_error(f"Invalid n value: {e}", "IFFT")
                    return
                
                # Parse sample rate
                try:
                    srate = float(edt_srate.Text)
                    if srate <= 0:
                        raise ValueError("Sample rate must be > 0")
                except ValueError as e:
                    show_error(f"Invalid sample rate: {e}", "IFFT")
                    return
                
                # Parse time offset
                try:
                    t0 = float(edt_t0.Text)
                except ValueError as e:
                    show_error(f"Invalid start time: {e}", "IFFT")
                    return
                
                # Get spectrum data (Y values are the amplitude spectrum)
                # Note: For proper IFFT, the input should be complex FFT output
                # But since we only have amplitude, we'll use it directly
                # This is a lossy reconstruction (no phase information)
                spectrum = np.array(y_vals, dtype=np.complex128)
                
                # Apply phase rotation if needed
                # 0: 0° (Real), 1: -90° (-j), 2: 180° (-1), 3: 90° (j)
                phase_idx = cb_phase.ItemIndex
                if phase_idx == 1:    # -90° (Sin)
                    spectrum *= -1j
                elif phase_idx == 2:  # 180° (-Cos)
                    spectrum *= -1
                elif phase_idx == 3:  # 90° (-Sin)
                    spectrum *= 1j
                
                # Revert the x2 factor applied in FFT for one-sided spectrum
                # We interpret indices 1:-1 as non-DC and non-Nyquist
                # BUT this depends on whether the original N was even or odd.
                # If n_output is even, last element is Nyquist.
                # If n_output is odd, last element is just high freq (doubled).
                
                is_even = (n_output % 2 == 0)
                
                if len(spectrum) > 1:
                    # Index 0 is DC (never doubled)
                    
                    if is_even:
                        # Even N: spectrum size is N/2 + 1. Last element is Nyquist.
                        # Do not halve DC (0) or Nyquist (-1)
                        if len(spectrum) > 2:
                            spectrum[1:-1] /= 2.0
                    else:
                        # Odd N: spectrum size is (N+1)/2. No Nyquist component.
                        # All components except DC (0) were doubled.
                        spectrum[1:] /= 2.0
                
                # Compute IRFFT
                # norm="forward" means no normalization (just like rfft with norm="forward" divided by n)
                # The spectrum already has correct magnitudes after reverting the x2 factor
                signal = irfft(spectrum, n=n_output, norm="forward")
                
                # Generate time axis
                dt = 1.0 / srate
                t = np.arange(n_output) * dt + t0
                
                # Create points for the reconstructed signal
                points = [Point(float(ti), float(yi)) for ti, yi in zip(t, signal)]
                
                # Create series
                ifft_series = Graph.TPointSeries()
                ifft_series.Points = points
                
                # Legend
                original_legend = series.LegendText if series.LegendText else "Series"
                ifft_series.LegendText = f"{original_legend} [IFFT, n={n_output}]"
                
                # Style - line only, no points
                ifft_series.Size = 0
                ifft_series.Style = 0
                ifft_series.LineSize = 2
                ifft_series.ShowLabels = False
                
                # Color
                color_val = safe_color(cb_color.Selected)
                ifft_series.FillColor = color_val
                ifft_series.FrameColor = color_val
                ifft_series.LineColor = color_val
                
                # Add to graph
                Graph.FunctionList.append(ifft_series)
                Graph.Update()
                
                show_info(
                    f"Reconstructed signal by IFFT:\n"
                    f"• n = {n_output} points\n"
                    f"• Δt = {dt:.6g}\n"
                    f"• Time range: [{t[0]:.4g}, {t[-1]:.4g}]",
                    "IFFT"
                )
                
                Form.ModalResult = 1  # mrOk
                
            except Exception as e:
                show_error(f"Error computing IFFT: {str(e)}", "IFFT")
        
        btn_compute.OnClick = on_compute
        
        # Show dialog
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="IFFT...", 
    OnExecute=ifft_dialog, 
    Hint="Compute inverse FFT to reconstruct time-domain signal",
    IconFile=os.path.join(os.path.dirname(__file__), "ifft_sm.png")
)

# Add to Plugins -> Analysis menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Analysis"])
