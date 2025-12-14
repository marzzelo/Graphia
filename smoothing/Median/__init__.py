# Plugin to apply selective Median filter to a point series
import os

# Import common module (automatically configures venv)
from common import (
    get_selected_point_series, show_error, show_info, safe_color,
    get_series_stats, Point, Graph, vcl
)

import numpy as np
from scipy.ndimage import median_filter, uniform_filter1d

PluginName = "Selective Median Filter"
PluginVersion = "1.3"
PluginDescription = "Detects outliers using a local median and replaces outlier segments using a line between bounding points; supports dynamic n·σ thresholding."


def apply_median_filter(Action):
    """Applies a selective median filter to the selected point series."""
    
    # Check that a TPointSeries is selected
    point_series, error_msg = get_selected_point_series()
    
    if point_series is None:
        show_error(error_msg, "Median Filter")
        return
    
    # Verify the series has points
    points = point_series.Points
    if not points or len(points) < 5:
        show_error(
            "The point series must have at least 5 points to apply the filter.",
            "Median Filter"
        )
        return
    
    # Get series statistics
    stats = get_series_stats(point_series)
    x_vals = stats['x_vals']
    y_vals = np.array(stats['y_vals'])
    y_min, y_max = stats['y_min'], stats['y_max']
    y_range = stats['y_range']
    n_points = stats['n_points']
    
    # Estimate sampling period from X spacing (used for window duration label)
    dx = np.diff(np.array(x_vals, dtype=float))
    ts_est = float(np.median(dx)) if dx.size > 0 else 0.0
    if not np.isfinite(ts_est) or ts_est <= 0:
        ts_est = float(np.mean(dx)) if dx.size > 0 else 0.0
    if not np.isfinite(ts_est) or ts_est <= 0:
        ts_est = 0.0

    # Suggested value for n (sigma multiplier)
    y_std = float(np.std(y_vals))
    suggested_n = 2.0
    
    # Create configuration form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Selective Median Filter"
        Form.Width = 450
        Form.Height = 520
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []  # Keep references
        
        # Series information
        lbl_info = vcl.TLabel(Form)
        lbl_info.Parent = Form
        lbl_info.Caption = f"Selected series: {n_points} points"
        lbl_info.Left = 20
        lbl_info.Top = 15
        lbl_info.Font.Style = {"fsBold"}
        labels.append(lbl_info)
        
        # Range information
        lbl_range = vcl.TLabel(Form)
        lbl_range.Parent = Form
        lbl_range.Caption = f"Y Range: [{y_min:.4g}, {y_max:.4g}]  |  σ = {y_std:.4g}"
        lbl_range.Left = 20
        lbl_range.Top = 35
        lbl_range.Font.Color = 0x666666
        labels.append(lbl_range)
        
        # Separador visual
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 55
        sep1.Width = 420
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Window size (kernel)
        lbl_kernel = vcl.TLabel(Form)
        lbl_kernel.Parent = Form
        lbl_kernel.Caption = "Window size (points):"
        lbl_kernel.Left = 20
        lbl_kernel.Top = 70
        labels.append(lbl_kernel)
        
        edit_kernel = vcl.TEdit(Form)
        edit_kernel.Parent = Form
        edit_kernel.Left = 200
        edit_kernel.Top = 67
        edit_kernel.Width = 60
        edit_kernel.Text = "5"
        
        lbl_kernel_hint = vcl.TLabel(Form)
        lbl_kernel_hint.Parent = Form
        lbl_kernel_hint.Caption = "(odd, ≥3)"
        lbl_kernel_hint.Left = 270
        lbl_kernel_hint.Top = 70
        lbl_kernel_hint.Font.Color = 0x808080
        labels.append(lbl_kernel_hint)

        lbl_kernel_time = vcl.TLabel(Form)
        lbl_kernel_time.Parent = Form
        lbl_kernel_time.Caption = ""
        lbl_kernel_time.Left = 330
        lbl_kernel_time.Top = 70
        lbl_kernel_time.Font.Color = 0x808080
        labels.append(lbl_kernel_time)
        
        # Threshold factor n (dynamic threshold = n * local_stdDev)
        lbl_thresh = vcl.TLabel(Form)
        lbl_thresh.Parent = Form
        lbl_thresh.Caption = "Threshold factor (n·σ):"
        lbl_thresh.Left = 20
        lbl_thresh.Top = 105
        labels.append(lbl_thresh)
        
        edit_n = vcl.TEdit(Form)
        edit_n.Parent = Form
        edit_n.Left = 200
        edit_n.Top = 102
        edit_n.Width = 60
        edit_n.Text = f"{suggested_n:.3g}"

        lbl_n_hint = vcl.TLabel(Form)
        lbl_n_hint.Parent = Form
        lbl_n_hint.Caption = "(|s - local_median| > n·local_stdDev)"
        lbl_n_hint.Left = 270
        lbl_n_hint.Top = 105
        lbl_n_hint.Font.Color = 0x808080
        labels.append(lbl_n_hint)
        
        # Help panel
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 20
        help_panel.Top = 140
        help_panel.Width = 400
        help_panel.Height = 130
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0  # Light blue background
        
        lbl_help_title = vcl.TLabel(Form)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "How does it work?"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)
        
        help_text = (
            f"1. Compute local median and local std dev in the selected window\n"
            f"2. Mark outliers where |s(t) - local_median| > n·local_stdDev\n"
            f"3. Replace consecutive outlier segments with a LINE between bounding points\n"
            f"\n"
            f"• Ideal for removing spikes while preserving the underlying trend\n"
            f"• Suggested n: {suggested_n:.3g} (global σ={y_std:.4g})"
        )
        
        lbl_help = vcl.TLabel(Form)
        lbl_help.Parent = help_panel
        lbl_help.Caption = help_text
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)
        
        # Option: create new series or modify existing
        lbl_option = vcl.TLabel(Form)
        lbl_option.Parent = Form
        lbl_option.Caption = "Output:"
        lbl_option.Left = 20
        lbl_option.Top = 285
        labels.append(lbl_option)
        
        rb_new = vcl.TRadioButton(Form)
        rb_new.Parent = Form
        rb_new.Caption = "Create new series"
        rb_new.Left = 120
        rb_new.Top = 285
        rb_new.Checked = True
        
        rb_replace = vcl.TRadioButton(Form)
        rb_replace.Parent = Form
        rb_replace.Caption = "Replace original series"
        rb_replace.Left = 120
        rb_replace.Top = 310

        chk_plot_threshold = vcl.TCheckBox(Form)
        chk_plot_threshold.Parent = Form
        chk_plot_threshold.Caption = "Plot threshold"
        chk_plot_threshold.Left = 120
        chk_plot_threshold.Top = 335
        chk_plot_threshold.Checked = False
        
        # Color for new series
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Color (new series):"
        lbl_color.Left = 20
        lbl_color.Top = 365
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 150
        cb_color.Top = 362
        cb_color.Width = 100
        cb_color.Selected = 0xFF00FF  # Magenta por defecto
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Apply"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 100
        btn_ok.Top = 400
        btn_ok.Width = 100
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 240
        btn_cancel.Top = 400

        def update_window_time(Sender=None):
            try:
                k = int(edit_kernel.Text)
                if k < 1:
                    lbl_kernel_time.Caption = ""
                    return
                if ts_est > 0:
                    # Duration in seconds for a k-point window (approx.)
                    dur = float(k) * ts_est
                    lbl_kernel_time.Caption = f"≈ {dur:.4g} s"
                else:
                    lbl_kernel_time.Caption = ""
            except Exception:
                lbl_kernel_time.Caption = ""

        edit_kernel.OnChange = update_window_time
        update_window_time(None)
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # Show dialog
        if Form.ShowModal() == 1:
            try:
                kernel_size = int(edit_kernel.Text)
                n_factor = float(edit_n.Text)
                
                if kernel_size < 3:
                    raise ValueError("Window size must be at least 3")
                
                # Asegurar que sea impar
                if kernel_size % 2 == 0:
                    kernel_size += 1
                
                if n_factor <= 0:
                    raise ValueError("n debe ser mayor que 0")
                
                # 1) Calcular mediana local (robusto) y std dev local (dinámico)
                y_median = median_filter(y_vals, size=kernel_size, mode='nearest')

                # local_stdDev via E[y^2] - (E[y])^2 in the window
                y_mean = uniform_filter1d(y_vals, size=kernel_size, mode='nearest')
                y_mean2 = uniform_filter1d(y_vals * y_vals, size=kernel_size, mode='nearest')
                var = y_mean2 - (y_mean * y_mean)
                var = np.maximum(var, 0.0)
                local_std = np.sqrt(var)

                # 2) Detectar outliers por desviación respecto a la mediana local
                deviation = np.abs(y_vals - y_median)
                dynamic_thr = n_factor * local_std
                outlier_mask = deviation > dynamic_thr

                # Tratar NaN como outlier (si existieran en la serie)
                outlier_mask = outlier_mask | np.isnan(y_vals)

                # 3) Reemplazar segmentos consecutivos de outliers con una recta
                #    definida por los puntos NO atípicos que los delimitan.
                y_filtered = y_vals.copy()
                outlier_indices = np.where(outlier_mask)[0]
                n_modified = int(outlier_indices.size)

                if n_modified > 0:
                    i = 0
                    while i < outlier_indices.size:
                        run_start = int(outlier_indices[i])
                        run_end = run_start
                        # Expandir el run
                        while i + 1 < outlier_indices.size and int(outlier_indices[i + 1]) == run_end + 1:
                            i += 1
                            run_end = int(outlier_indices[i])

                        # Buscar punto delimitador a la izquierda
                        left = run_start - 1
                        while left >= 0 and outlier_mask[left]:
                            left -= 1

                        # Buscar punto delimitador a la derecha
                        right = run_end + 1
                        while right < n_points and outlier_mask[right]:
                            right += 1

                        if left >= 0 and right < n_points:
                            x0 = float(x_vals[left])
                            y0 = float(y_vals[left])
                            x1 = float(x_vals[right])
                            y1 = float(y_vals[right])

                            denom = (x1 - x0)
                            if denom == 0:
                                # X duplicado: no se puede interpolar; usar valor izquierdo
                                for j in range(run_start, run_end + 1):
                                    y_filtered[j] = y0
                            else:
                                for j in range(run_start, run_end + 1):
                                    xj = float(x_vals[j])
                                    y_filtered[j] = y0 + (y1 - y0) * ((xj - x0) / denom)
                        elif left >= 0:
                            # Segmento al final sin delimitador derecho: mantener último valor válido
                            y0 = float(y_vals[left])
                            for j in range(run_start, run_end + 1):
                                y_filtered[j] = y0
                        elif right < n_points:
                            # Segmento al inicio sin delimitador izquierdo: mantener primer valor válido
                            y1 = float(y_vals[right])
                            for j in range(run_start, run_end + 1):
                                y_filtered[j] = y1
                        else:
                            # Todo es atípico: fallback a mediana local
                            for j in range(run_start, run_end + 1):
                                y_filtered[j] = y_median[j]

                        i += 1
                
                # Crear nuevos puntos
                new_points = [Point(x, y) for x, y in zip(x_vals, y_filtered)]
                
                if rb_new.Checked:
                    # Crear nueva serie
                    new_series = Graph.TPointSeries()
                    new_series.PointType = point_series.PointType
                    new_series.Points = new_points
                    
                    # Copy display properties
                    original_legend = point_series.LegendText
                    new_series.LegendText = f"{original_legend} [Median k={kernel_size}, n={n_factor:.3g}]"
                    new_series.Size = point_series.Size
                    new_series.Style = point_series.Style
                    new_series.LineSize = point_series.LineSize
                    new_series.ShowLabels = point_series.ShowLabels
                    
                    # Usar el color seleccionado
                    color_val = safe_color(cb_color.Selected)
                    new_series.FillColor = color_val
                    new_series.FrameColor = color_val
                    new_series.LineColor = color_val
                    
                    Graph.FunctionList.append(new_series)
                else:
                    # Reemplazar puntos en la serie original
                    point_series.Points = new_points
                    original_legend = point_series.LegendText
                    if "[Median" not in original_legend:
                        point_series.LegendText = f"{original_legend} [Median k={kernel_size}, n={n_factor:.3g}]"

                # Optional: plot dynamic threshold bands (local_median ± n*local_std)
                if chk_plot_threshold.Checked:
                    thr_upper = y_median + dynamic_thr
                    thr_lower = y_median - dynamic_thr

                    band_color = 0x888888  # gray (BGR)

                    upper_series = Graph.TPointSeries()
                    upper_series.PointType = Graph.ptCartesian
                    upper_series.Points = [Point(x, y) for x, y in zip(x_vals, thr_upper)]
                    upper_series.LegendText = f"{point_series.LegendText} (threshold +)"
                    upper_series.Size = 0
                    upper_series.Style = 0
                    upper_series.LineSize = 1
                    upper_series.LineStyle = 0  
                    upper_series.ShowLabels = False
                    col = safe_color(band_color)
                    upper_series.FillColor = col
                    upper_series.FrameColor = col
                    upper_series.LineColor = col

                    lower_series = Graph.TPointSeries()
                    lower_series.PointType = Graph.ptCartesian
                    lower_series.Points = [Point(x, y) for x, y in zip(x_vals, thr_lower)]
                    lower_series.LegendText = f"{point_series.LegendText} (threshold -)"
                    lower_series.Size = 0
                    lower_series.Style = 0
                    lower_series.LineSize = 1
                    lower_series.LineStyle = 0  
                    lower_series.ShowLabels = False
                    lower_series.FillColor = col
                    lower_series.FrameColor = col
                    lower_series.LineColor = col

                    Graph.FunctionList.append(upper_series)
                    Graph.FunctionList.append(lower_series)
                
                Graph.Update()
                
                # Show summary
                show_info(
                    f"Filter applied successfully.\n\nPoints modified: {n_modified} of {n_points} ({100*n_modified/n_points:.1f}%)",
                    "Median Filter"
                )
                
            except ValueError as e:
                show_error(f"Parameter error: {str(e)}", "Median Filter")
            except Exception as e:
                show_error(f"Error applying filter: {str(e)}", "Median Filter")
    finally:
        Form.Free()


# Create action for menu
MedianFilterAction = Graph.CreateAction(
    Caption="Median Filter...",
    OnExecute=apply_median_filter,
    Hint="Applies a selective median filter to remove outliers/spikes.",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "Median_sm.png")
)

# Add action to 'Smoothing' submenu within 'Plugins'
Graph.AddActionToMainMenu(MedianFilterAction, TopMenu="Plugins", SubMenus=["Graphîa", "Smoothing"])
