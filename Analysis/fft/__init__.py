"""
FFT - Plugin para calcular el espectro de amplitud mediante Transformada Rápida de Fourier
Usa scipy.fft.rfft para señales reales.
"""

import Graph
import vcl  # type: ignore
import os
import math

# Import common utilities
from common import (
    setup_venv, get_selected_point_series, show_error, show_info, 
    get_series_data, Point, safe_color, get_series_stats
)

# Import numpy and scipy
import numpy as np
from scipy.fft import rfft, rfftfreq

PluginName = "FFT"
PluginVersion = "1.3"
PluginDescription = "Compute amplitude spectrum using FFT (scipy.fft.rfft)."


def next_power_of_two(n):
    """Returns the smallest power of 2 greater than or equal to n."""
    if n <= 0:
        return 1
    return 2 ** math.ceil(math.log2(n))


def fft_dialog(Action):
    """
    Shows a dialog to configure and compute FFT from the selected series.
    """
    # Get selected series
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "FFT")
        return

    # Get current data
    x_vals, y_vals = get_series_data(series)
    
    if len(y_vals) < 2:
        show_info("The selected series must have at least 2 points.", "FFT")
        return

    # Calculate stats for info
    stats = get_series_stats(series)
    n_points = stats['n_points']
    x_min = stats['x_min']
    x_max = stats['x_max']
    dx_avg = stats['dx_avg']
    
    # Default n = number of points in the series (no zero-padding by default)
    n_default = n_points
    n_power2 = next_power_of_two(n_points)
    
    # Estimate sample rate from average dx
    if dx_avg > 0:
        srate_estimated = 1.0 / dx_avg
    else:
        srate_estimated = 1.0
    
    # Default max frequency = Nyquist (fs/2)
    f_max_default = srate_estimated / 2.0
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "FFT - Espectro de Amplitud"
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
        lbl_help_title.Caption = "Transformada Rápida de Fourier (RFFT)"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        series_name = series.LegendText if series.LegendText else "(sin nombre)"
        lbl_series = vcl.TLabel(help_panel)
        lbl_series.Parent = help_panel
        lbl_series.Caption = f"Serie: {series_name}"
        lbl_series.Left = 10
        lbl_series.Top = 28
        lbl_series.Font.Color = 0x804000
        labels.append(lbl_series)
        
        lbl_info = vcl.TLabel(help_panel)
        lbl_info.Parent = help_panel
        lbl_info.Caption = f"N = {n_points} puntos  |  X ∈ [{x_min:.4g}, {x_max:.4g}]  |  Δx ≈ {dx_avg:.6g}  |  fs ≈ {srate_estimated:.4g}"
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
        lbl_params.Caption = "Parámetros de FFT"
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
        
        # n (FFT length)
        lbl_n = vcl.TLabel(Form)
        lbl_n.Parent = pnl_params
        lbl_n.Caption = "n (longitud FFT):"
        lbl_n.Left = 15
        lbl_n.Top = 15
        labels.append(lbl_n)
        
        edt_n = vcl.TEdit(Form)
        edt_n.Parent = pnl_params
        edt_n.Left = 130
        edt_n.Top = 12
        edt_n.Width = 80
        edt_n.Text = str(n_default)
        
        lbl_n_info = vcl.TLabel(Form)
        lbl_n_info.Parent = pnl_params
        lbl_n_info.Caption = f"(default = N, próxima potencia de 2 = {n_power2})"
        lbl_n_info.Left = 220
        lbl_n_info.Top = 15
        lbl_n_info.Font.Color = 0x666666
        labels.append(lbl_n_info)
        
        # Sample rate override
        lbl_srate = vcl.TLabel(Form)
        lbl_srate.Parent = pnl_params
        lbl_srate.Caption = "Sample rate (fs):"
        lbl_srate.Left = 15
        lbl_srate.Top = 45
        labels.append(lbl_srate)
        
        edt_srate = vcl.TEdit(Form)
        edt_srate.Parent = pnl_params
        edt_srate.Left = 130
        edt_srate.Top = 42
        edt_srate.Width = 80
        edt_srate.Text = f"{srate_estimated:.6g}"
        
        lbl_srate_info = vcl.TLabel(Form)
        lbl_srate_info.Parent = pnl_params
        lbl_srate_info.Caption = "(calculado de Δx promedio, modificar si es necesario)"
        lbl_srate_info.Left = 220
        lbl_srate_info.Top = 45
        lbl_srate_info.Font.Color = 0x666666
        labels.append(lbl_srate_info)
        
        # Max frequency cutoff
        lbl_fmax = vcl.TLabel(Form)
        lbl_fmax.Parent = pnl_params
        lbl_fmax.Caption = "Frecuencia máx:"
        lbl_fmax.Left = 15
        lbl_fmax.Top = 75
        labels.append(lbl_fmax)
        
        edt_fmax = vcl.TEdit(Form)
        edt_fmax.Parent = pnl_params
        edt_fmax.Left = 130
        edt_fmax.Top = 72
        edt_fmax.Width = 80
        edt_fmax.Text = f"{f_max_default:.6g}"
        
        lbl_fmax_info = vcl.TLabel(Form)
        lbl_fmax_info.Parent = pnl_params
        lbl_fmax_info.Caption = f"(recorta salida, default = fs/2 = {f_max_default:.4g})"
        lbl_fmax_info.Left = 220
        lbl_fmax_info.Top = 75
        lbl_fmax_info.Font.Color = 0x666666
        labels.append(lbl_fmax_info)
        
        # Output info
        lbl_output_info = vcl.TLabel(Form)
        lbl_output_info.Parent = pnl_params
        lbl_output_info.Caption = f"Frecuencia Nyquist: fs/2 = {srate_estimated/2:.4g}"
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
        lbl_output.Caption = "Salida"
        lbl_output.Left = 10
        lbl_output.Top = 273
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Color selector
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Color del espectro:"
        lbl_color.Left = 20
        lbl_color.Top = 300
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 140
        cb_color.Top = 297
        cb_color.Width = 100
        cb_color.Selected = 0x00AA00  # Green by default
        
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
        btn_compute.Caption = "Calcular FFT"
        btn_compute.Left = 140
        btn_compute.Top = 350
        btn_compute.Width = 110
        btn_compute.Height = 30
        btn_compute.Default = True
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancelar"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 260
        btn_cancel.Top = 350
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        def on_compute(Sender):
            try:
                # Parse n
                try:
                    n_fft = int(edt_n.Text)
                    if n_fft < 1:
                        raise ValueError("n debe ser >= 1")
                except ValueError as e:
                    show_error(f"Valor de n inválido: {e}", "FFT")
                    return
                
                # Parse sample rate
                try:
                    srate = float(edt_srate.Text)
                    if srate <= 0:
                        raise ValueError("Sample rate debe ser > 0")
                except ValueError as e:
                    show_error(f"Sample rate inválido: {e}", "FFT")
                    return
                
                # Parse max frequency cutoff
                try:
                    f_max = float(edt_fmax.Text)
                    if f_max <= 0:
                        raise ValueError("Frecuencia máxima debe ser > 0")
                except ValueError as e:
                    show_error(f"Frecuencia máxima inválida: {e}", "FFT")
                    return
                
                # Get signal data
                signal = np.array(y_vals)
                
                # 1. Compute RFFT with n defined
                # Automatically pads with zeros if n > len(signal)
                fourier = rfft(signal, n=n_fft, norm="forward")
                
                # 2. Magnitude with *2 adjustment for one-sided spectrum
                amp = np.abs(fourier)
                amp[1:-1] *= 2  # Adjust non-DC and non-Nyquist components
                
                # 3. IMPORTANT: Frequency axis MUST use n_fft, not N
                hz = rfftfreq(n_fft, 1/srate)
                
                # 4. Cutoff: filter to max frequency
                mask = hz <= f_max
                hz_filtered = hz[mask]
                amp_filtered = amp[mask]
                
                # Create points for the spectrum
                points = [Point(float(f), float(a)) for f, a in zip(hz_filtered, amp_filtered)]
                
                # Create series
                fft_series = Graph.TPointSeries()
                fft_series.Points = points
                
                # Legend
                original_legend = series.LegendText if series.LegendText else "Serie"
                fft_series.LegendText = f"{original_legend} [FFT, n={n_fft}]"
                
                # Style - line only, no points
                fft_series.Size = 0
                fft_series.Style = 0
                fft_series.LineSize = 2
                fft_series.ShowLabels = False
                
                # Color
                color_val = safe_color(cb_color.Selected)
                fft_series.FillColor = color_val
                fft_series.FrameColor = color_val
                fft_series.LineColor = color_val
                
                # Add to graph
                Graph.FunctionList.append(fft_series)
                Graph.Update()
                
                show_info(
                    f"Espectro FFT calculado:\n"
                    f"• n = {n_fft} puntos\n"
                    f"• Resolución frecuencial: Δf = {srate/n_fft:.6g} Hz\n"
                    f"• Rango de salida: 0 a {hz_filtered[-1]:.4g} Hz",
                    "FFT"
                )
                
                Form.ModalResult = 1  # mrOk
                
            except Exception as e:
                show_error(f"Error calculando FFT: {str(e)}", "FFT")
        
        btn_compute.OnClick = on_compute
        
        # Show dialog
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="FFT...", 
    OnExecute=fft_dialog, 
    Hint="Compute amplitude spectrum using FFT (Fast Fourier Transform)",
    IconFile=os.path.join(os.path.dirname(__file__), "fft_sm.png")
)

# Add to Plugins -> Analysis menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Analysis"])
