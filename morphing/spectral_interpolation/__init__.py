# Plugin for Spectral Interpolation - Fill gaps in signals using FFT-based interpolation
import os
import copy

# Import common module
from common import (
    get_selected_point_series, show_error, show_info, 
    safe_color, Point, Graph, vcl, get_series_data_np
)

import numpy as np
import scipy.fftpack
import scipy.signal

PluginName = "Spectral Interpolation"
PluginVersion = "1.0"
PluginDescription = "Fills gaps in signals using spectral (FFT-based) interpolation."

# Interpolation modes for when data is missing on one side
INTERP_MODES = [
    "Average (pre + post)",      # Default: average of both sides
    "Pre-gap only",              # Use only data before the gap
    "Post-gap only",             # Use only data after the gap
    "Weighted average"           # Weighted by proximity to gap edges
]


def spectral_interpolation(Action):
    """Performs spectral interpolation to fill a gap in the selected point series."""
    
    # Get selected series
    point_series, error_msg = get_selected_point_series()
    if point_series is None:
        show_error(error_msg or "You must select a point series (TPointSeries).", "Spectral Interpolation")
        return
    
    # Get original data using common utility
    x_orig, y_orig = get_series_data_np(point_series)
    if len(x_orig) < 10:
        show_error("The series must have at least 10 points.", "Spectral Interpolation")
        return
    
    # Calculate sampling period
    dx = np.diff(x_orig)
    current_period = float(np.mean(dx))
    x_min, x_max = float(x_orig.min()), float(x_orig.max())
    n_points = len(x_orig)
    
    # Get current view window limits for default gap boundaries
    try:
        view_x_min = Graph.Axes.xAxis.Min
        view_x_max = Graph.Axes.xAxis.Max
        # Use view limits directly, clamped to data range
        default_xa = float(max(view_x_min, x_min))
        default_xb = float(min(view_x_max, x_max))
        if default_xa >= default_xb:
            # Fallback to middle third of the data
            range_third = (x_max - x_min) / 3.0
            default_xa = x_min + range_third
            default_xb = x_max - range_third
    except Exception:
        # Fallback to middle third of the data
        range_third = (x_max - x_min) / 3.0
        default_xa = x_min + range_third
        default_xb = x_max - range_third
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Spectral Interpolation - Fill Gap with Synthetic Data"
        Form.Width = 450
        Form.Height = 470
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []
        
        # Original series info
        lbl_info = vcl.TLabel(Form)
        lbl_info.Parent = Form
        lbl_info.Caption = "Original series:"
        lbl_info.Left = 20
        lbl_info.Top = 15
        lbl_info.Font.Style = {"fsBold"}
        labels.append(lbl_info)
        
        info_text = (
            f"Points: {n_points}  |  "
            f"X: [{x_min:.4g}, {x_max:.4g}]  |  "
            f"Ts ≈ {current_period:.4g}"
        )
        lbl_info_val = vcl.TLabel(Form)
        lbl_info_val.Parent = Form
        lbl_info_val.Caption = info_text
        lbl_info_val.Left = 20
        lbl_info_val.Top = 35
        lbl_info_val.Font.Color = 0x666666
        labels.append(lbl_info_val)
        
        # Separator
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 60
        sep1.Width = 420
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Gap boundaries section
        lbl_gap = vcl.TLabel(Form)
        lbl_gap.Parent = Form
        lbl_gap.Caption = "Gap boundaries (data to replace):"
        lbl_gap.Left = 20
        lbl_gap.Top = 75
        lbl_gap.Font.Style = {"fsBold"}
        labels.append(lbl_gap)
        
        # Xa (start of gap)
        lbl_xa = vcl.TLabel(Form)
        lbl_xa.Parent = Form
        lbl_xa.Caption = "Gap start (Xa):"
        lbl_xa.Left = 20
        lbl_xa.Top = 105
        labels.append(lbl_xa)
        
        edt_xa = vcl.TEdit(Form)
        edt_xa.Parent = Form
        edt_xa.Left = 150
        edt_xa.Top = 102
        edt_xa.Width = 120
        edt_xa.Text = f"{default_xa:.6g}"
        
        # Xb (end of gap)
        lbl_xb = vcl.TLabel(Form)
        lbl_xb.Parent = Form
        lbl_xb.Caption = "Gap end (Xb):"
        lbl_xb.Left = 20
        lbl_xb.Top = 135
        labels.append(lbl_xb)
        
        edt_xb = vcl.TEdit(Form)
        edt_xb.Parent = Form
        edt_xb.Left = 150
        edt_xb.Top = 132
        edt_xb.Width = 120
        edt_xb.Text = f"{default_xb:.6g}"
        
        # Gap info label (dynamic)
        lbl_gap_info = vcl.TLabel(Form)
        lbl_gap_info.Parent = Form
        lbl_gap_info.Caption = ""
        lbl_gap_info.Left = 280
        lbl_gap_info.Top = 117
        lbl_gap_info.Font.Color = 0x808080
        labels.append(lbl_gap_info)
        
        # Separator
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 165
        sep2.Width = 420
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        # Interpolation mode
        lbl_mode = vcl.TLabel(Form)
        lbl_mode.Parent = Form
        lbl_mode.Caption = "Interpolation mode:"
        lbl_mode.Left = 20
        lbl_mode.Top = 180
        labels.append(lbl_mode)
        
        cb_mode = vcl.TComboBox(Form)
        cb_mode.Parent = Form
        cb_mode.Left = 150
        cb_mode.Top = 177
        cb_mode.Width = 200
        cb_mode.Style = "csDropDownList"
        for mode in INTERP_MODES:
            cb_mode.Items.Add(mode)
        cb_mode.ItemIndex = 0
        
        # Data availability info
        lbl_avail = vcl.TLabel(Form)
        lbl_avail.Parent = Form
        lbl_avail.Caption = ""
        lbl_avail.Left = 20
        lbl_avail.Top = 210
        lbl_avail.Font.Color = 0x008000
        labels.append(lbl_avail)
        
        # New series color
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Result series color:"
        lbl_color.Left = 20
        lbl_color.Top = 245
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 150
        cb_color.Top = 242
        cb_color.Width = 120
        cb_color.Selected = 0x00AAFF  # Orange por defecto
        
        # Method information panel
        pnl_help = vcl.TPanel(Form)
        pnl_help.Parent = Form
        pnl_help.Left = 20
        pnl_help.Top = 280
        pnl_help.Width = 400
        pnl_help.Height = 90
        pnl_help.BevelOuter = "bvLowered"
        pnl_help.Color = 0xFFF8F0
        
        help_text = (
            "Spectral Interpolation fills gaps by:\n"
            "1. Computing FFT of segments before and after the gap\n"
            "2. Averaging the spectra to estimate the missing region\n"
            "3. Applying IFFT to get time-domain data\n"
            "4. Detrending and adding linear ramp to match gap edges"
        )
        
        lbl_help = vcl.TLabel(Form)
        lbl_help.Parent = pnl_help
        lbl_help.Caption = help_text
        lbl_help.Left = 10
        lbl_help.Top = 8
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Interpolate"
        btn_ok.ModalResult = 1
        btn_ok.Default = True
        btn_ok.Left = 120
        btn_ok.Top = 380
        btn_ok.Width = 100
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        btn_cancel.Left = 235
        btn_cancel.Top = 380
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # ========== Event handlers ==========
        def update_gap_info(Sender):
            """Update gap information and data availability"""
            try:
                xa = float(edt_xa.Text)
                xb = float(edt_xb.Text)
                
                if xa >= xb:
                    lbl_gap_info.Caption = "(Xa must be < Xb)"
                    lbl_gap_info.Font.Color = 0x0000FF  # Red
                    lbl_avail.Caption = ""
                    btn_ok.Enabled = False
                    return
                
                # Calculate gap size in points
                gap_size = int((xb - xa) / current_period)
                lbl_gap_info.Caption = f"(≈ {gap_size} points)"
                lbl_gap_info.Font.Color = 0x808080
                
                # Check data availability before and after gap
                # Find indices for gap boundaries
                idx_a = np.searchsorted(x_orig, xa)
                idx_b = np.searchsorted(x_orig, xb)
                
                points_before = idx_a
                points_after = n_points - idx_b
                
                # Check if we have enough data
                has_pre = points_before >= gap_size
                has_post = points_after >= gap_size
                
                if has_pre and has_post:
                    lbl_avail.Caption = f"✓ Pre-gap: {points_before} pts  |  Post-gap: {points_after} pts"
                    lbl_avail.Font.Color = 0x008000  # Green
                    cb_mode.Enabled = True
                    btn_ok.Enabled = True
                elif has_pre:
                    lbl_avail.Caption = f"⚠ Pre-gap: {points_before} pts  |  Post-gap: {points_after} pts (insufficient)"
                    lbl_avail.Font.Color = 0x0080FF  # Orange
                    cb_mode.ItemIndex = 1  # Pre-gap only
                    cb_mode.Enabled = True
                    btn_ok.Enabled = True
                elif has_post:
                    lbl_avail.Caption = f"⚠ Pre-gap: {points_before} pts (insufficient)  |  Post-gap: {points_after} pts"
                    lbl_avail.Font.Color = 0x0080FF  # Orange
                    cb_mode.ItemIndex = 2  # Post-gap only
                    cb_mode.Enabled = True
                    btn_ok.Enabled = True
                else:
                    lbl_avail.Caption = f"✗ Insufficient data on both sides ({points_before} / {points_after} pts)"
                    lbl_avail.Font.Color = 0x0000FF  # Red
                    btn_ok.Enabled = False
                    
            except Exception as ex:
                lbl_gap_info.Caption = "(invalid)"
                lbl_gap_info.Font.Color = 0x0000FF
                lbl_avail.Caption = ""
                btn_ok.Enabled = False
        
        # Assign event handlers
        edt_xa.OnChange = update_gap_info
        edt_xb.OnChange = update_gap_info
        
        # Initial update
        update_gap_info(None)
        
        if Form.ShowModal() == 1:
            try:
                # Get parameters
                xa = float(edt_xa.Text)
                xb = float(edt_xb.Text)
                mode_idx = cb_mode.ItemIndex
                color = int(cb_color.Selected) & 0xFFFFFF
                
                if xa >= xb:
                    raise ValueError("Gap start (Xa) must be less than gap end (Xb)")
                
                # Find indices for gap boundaries
                idx_a = int(np.searchsorted(x_orig, xa))
                idx_b = int(np.searchsorted(x_orig, xb))
                
                # Gap size in points
                gap_size = idx_b - idx_a
                if gap_size < 2:
                    raise ValueError("Gap must contain at least 2 points")
                
                # Check data availability
                points_before = idx_a
                points_after = n_points - idx_b
                
                has_pre = points_before >= gap_size
                has_post = points_after >= gap_size
                
                # Determine which mode to use based on data availability
                if mode_idx == 0:  # Average (pre + post)
                    if not has_pre and not has_post:
                        raise ValueError("Insufficient data on both sides of the gap")
                    elif not has_pre:
                        mode_idx = 2  # Fall back to post-gap only
                    elif not has_post:
                        mode_idx = 1  # Fall back to pre-gap only
                elif mode_idx == 1:  # Pre-gap only
                    if not has_pre:
                        raise ValueError("Insufficient data before the gap")
                elif mode_idx == 2:  # Post-gap only
                    if not has_post:
                        raise ValueError("Insufficient data after the gap")
                elif mode_idx == 3:  # Weighted average
                    if not has_pre and not has_post:
                        raise ValueError("Insufficient data on both sides of the gap")
                    elif not has_pre:
                        mode_idx = 2
                    elif not has_post:
                        mode_idx = 1
                
                # Get data segments for FFT
                if mode_idx == 0 or mode_idx == 3:  # Average or Weighted
                    # Pre-gap segment (same size as gap, just before it)
                    pre_start = idx_a - gap_size
                    pre_end = idx_a
                    segment_pre = y_orig[pre_start:pre_end]
                    
                    # Post-gap segment (same size as gap, just after it)
                    post_start = idx_b
                    post_end = idx_b + gap_size
                    segment_post = y_orig[post_start:post_end]
                    
                    # Compute FFTs
                    fft_pre = scipy.fftpack.fft(segment_pre)
                    fft_post = scipy.fftpack.fft(segment_post)
                    
                    if mode_idx == 0:  # Simple average
                        fft_avg = (fft_pre + fft_post) / 2
                    else:  # Weighted average (mode_idx == 3)
                        # Weight by distance - closer segments get more weight
                        # For now, use 50/50 (could be enhanced with user input)
                        weight_pre = 0.5
                        weight_post = 0.5
                        fft_avg = weight_pre * fft_pre + weight_post * fft_post
                    
                    method_name = "avg(pre+post)" if mode_idx == 0 else "weighted"
                    
                elif mode_idx == 1:  # Pre-gap only
                    pre_start = idx_a - gap_size
                    pre_end = idx_a
                    segment_pre = y_orig[pre_start:pre_end]
                    fft_avg = scipy.fftpack.fft(segment_pre)
                    method_name = "pre-gap"
                    
                elif mode_idx == 2:  # Post-gap only
                    post_start = idx_b
                    post_end = idx_b + gap_size
                    segment_post = y_orig[post_start:post_end]
                    fft_avg = scipy.fftpack.fft(segment_post)
                    method_name = "post-gap"
                
                # Apply inverse FFT and detrend
                mixed_data = scipy.signal.detrend(np.real(scipy.fftpack.ifft(fft_avg)))
                
                # Get values at gap boundaries (the points just OUTSIDE the gap)
                # idx_a-1 is the last point BEFORE the gap
                # idx_b is the first point AFTER the gap
                y_before_gap = float(y_orig[idx_a - 1]) if idx_a > 0 else float(y_orig[0])
                y_after_gap = float(y_orig[idx_b]) if idx_b < n_points else float(y_orig[-1])
                
                # We're replacing points at indices [idx_a, idx_a+1, ..., idx_b-1]
                # The interpolated segment should transition smoothly FROM y_before_gap TO y_after_gap
                # but the actual replaced points are BETWEEN these boundary points
                # So we use gap_size+2 points and take only the interior ones
                line_data_full = np.linspace(y_before_gap, y_after_gap, gap_size + 2)
                line_data = line_data_full[1:-1]  # Exclude the boundary points themselves
                
                # Combine detrended FFT result with linear ramp
                interpolated = mixed_data + line_data
                
                # Apply tapered correction to ensure smooth transition at boundaries
                # Calculate errors at the edges
                # The first interpolated point should be close to y_before_gap (continuing the trend)
                # The last interpolated point should be close to y_after_gap (continuing the trend)
                target_start = line_data[0]   # Expected value at first interior point
                target_end = line_data[-1]    # Expected value at last interior point
                
                start_error = target_start - interpolated[0]
                end_error = target_end - interpolated[-1]
                
                # Create tapering weights (1 at edges, 0 at center)
                t = np.linspace(0, 1, gap_size)
                taper_start = 1 - t  # Goes from 1 to 0
                taper_end = t        # Goes from 0 to 1
                
                # Apply tapered corrections
                interpolated = interpolated + start_error * taper_start + end_error * taper_end
                
                # Create the result signal (copy original and replace gap)
                y_result = copy.deepcopy(y_orig)
                y_result[idx_a:idx_b] = interpolated
                
                # Create new series with the result
                new_points = [Point(float(x), float(y)) for x, y in zip(x_orig, y_result)]
                
                new_series = Graph.TPointSeries()
                new_series.PointType = Graph.ptCartesian
                new_series.Points = new_points
                new_series.LegendText = f"{point_series.LegendText} (spectral interp {method_name})"
                new_series.Size = 0
                new_series.Style = 0
                new_series.LineSize = 1
                new_series.ShowLabels = False
                
                color_val = safe_color(color)
                new_series.FillColor = color_val
                new_series.FrameColor = color_val
                new_series.LineColor = color_val
                
                Graph.FunctionList.append(new_series)
                Graph.Update()
                
            except Exception as e:
                show_error(f"Error during interpolation: {str(e)}", "Spectral Interpolation")
    
    finally:
        Form.Free()


# Create action for menu
SpectralInterpAction = Graph.CreateAction(
    Caption="Spectral Interpolation...",
    OnExecute=spectral_interpolation,
    Hint="Fill gaps in signals using spectral (FFT-based) interpolation.",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "SpectralInterp_sm.png")
)

# Add action to Plugins menu
Graph.AddActionToMainMenu(SpectralInterpAction, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"])  # type: ignore
