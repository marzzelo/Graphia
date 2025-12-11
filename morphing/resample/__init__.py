# Plugin to resample a point series with interpolation
import os

# Import common module
from common import (
    get_selected_point_series, show_error, show_info, 
    safe_color, Point, Graph, vcl, get_series_data_np
)

import numpy as np
from scipy.interpolate import CubicSpline, PchipInterpolator, Akima1DInterpolator
from scipy.signal import decimate

PluginName = "Resample"
PluginVersion = "1.1"
PluginDescription = "Resamples a point series using interpolation."

# Available interpolation methods
INTERP_METHODS = [
    "np.interp (lineal)",
    "CubicSpline",
    "PchipInterpolator",
    "Akima1DInterpolator"
]

# Resampling modes
RESAMPLE_MODES = [
    "New Sampling Period",
    "New Sampling Frequency",
    "New Number of Points",
    "Resample by Factor"
]


def resample_series(Action):
    """Resamples the selected point series."""
    
    # Get selected series
    point_series, error_msg = get_selected_point_series()
    if point_series is None:
        show_error(error_msg or "You must select a point series (TPointSeries).", "Resample")
        return
    
    # Get original data using common utility
    x_orig, y_orig = get_series_data_np(point_series)
    if len(x_orig) < 2:
        show_error("The series must have at least 2 points.", "Resample")
        return
    
    # Calcular periodo de muestreo actual (promedio)
    dx = np.diff(x_orig)
    current_period = np.mean(dx)
    x_min, x_max = x_orig.min(), x_orig.max()
    n_points = len(x_orig)
    
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Resample - Resampling with Interpolation"
        Form.Width = 420
        Form.Height = 395
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
            f"Ts ≈ {current_period:.4g}  |  "
            f"Fs ≈ {1.0/current_period:.4g}"
        )
        lbl_info_val = vcl.TLabel(Form)
        lbl_info_val.Parent = Form
        lbl_info_val.Caption = info_text
        lbl_info_val.Left = 20
        lbl_info_val.Top = 35
        lbl_info_val.Font.Color = 0x666666
        labels.append(lbl_info_val)
        
        # Separador
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 60
        sep1.Width = 390
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Resampling mode selector
        cmb_mode = vcl.TComboBox(Form)
        cmb_mode.Parent = Form
        cmb_mode.Left = 20
        cmb_mode.Top = 77
        cmb_mode.Width = 170
        cmb_mode.Style = 2  # csDropDownList
        for mode in RESAMPLE_MODES:
            cmb_mode.Items.Add(mode)
        cmb_mode.ItemIndex = 0
        
        # Value input field
        edt_value = vcl.TEdit(Form)
        edt_value.Parent = Form
        edt_value.Left = 200
        edt_value.Top = 77
        edt_value.Width = 100
        edt_value.Text = f"{current_period:.6g}"
        
        # Label for resulting point count
        lbl_new_points = vcl.TLabel(Form)
        lbl_new_points.Parent = Form
        lbl_new_points.Caption = f"(≈ {n_points} points)"
        lbl_new_points.Left = 310
        lbl_new_points.Top = 80
        lbl_new_points.Font.Color = 0x808080
        labels.append(lbl_new_points)
        
        # Interpolation method
        lbl_method = vcl.TLabel(Form)
        lbl_method.Parent = Form
        lbl_method.Caption = "Interpolation method:"
        lbl_method.Left = 20
        lbl_method.Top = 120
        labels.append(lbl_method)
        
        cb_method = vcl.TComboBox(Form)
        cb_method.Parent = Form
        cb_method.Left = 200
        cb_method.Top = 117
        cb_method.Width = 180
        cb_method.Style = "csDropDownList"
        for method in INTERP_METHODS:
            cb_method.Items.Add(method)
        cb_method.ItemIndex = 1  # CubicSpline por defecto
        
        # Downsampling filter type selector
        lbl_ftype = vcl.TLabel(Form)
        lbl_ftype.Parent = Form
        lbl_ftype.Caption = "Downsample filter type:"
        lbl_ftype.Left = 20
        lbl_ftype.Top = 160
        lbl_ftype.Visible = False  # Initially hidden
        labels.append(lbl_ftype)
        
        cb_ftype = vcl.TComboBox(Form)
        cb_ftype.Parent = Form
        cb_ftype.Left = 200
        cb_ftype.Top = 157
        cb_ftype.Width = 180
        cb_ftype.Style = "csDropDownList"
        cb_ftype.Items.Add("fir (default)")
        cb_ftype.Items.Add("iir")
        cb_ftype.Items.Add("None (use interpolation)")
        cb_ftype.ItemIndex = 0  # fir por defecto
        cb_ftype.Visible = False  # Initially hidden
        
        # New series color
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "New series color:"
        lbl_color.Left = 20
        lbl_color.Top = 200
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 200
        cb_color.Top = 197
        cb_color.Width = 120
        cb_color.Selected = 0x00AA00  # Verde por defecto
        
        # Method information panel
        pnl_help = vcl.TPanel(Form)
        pnl_help.Parent = Form
        pnl_help.Left = 20
        pnl_help.Top = 240
        pnl_help.Width = 370
        pnl_help.Height = 70
        pnl_help.BevelOuter = "bvLowered"
        pnl_help.Color = 0xFFF8F0
        
        help_text = (
            "• np.interp: Simple linear interpolation\n"
            "• CubicSpline: Smooth cubic spline (may oscillate)\n"
            "• Pchip: Monotonic, preserves local shape\n"
            "• Akima: Smooth, reduces oscillations in noisy data"
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
        btn_ok.Caption = "Resample"
        btn_ok.ModalResult = 1
        btn_ok.Default = True
        btn_ok.Left = 110
        btn_ok.Top = 325
        btn_ok.Width = 100
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        btn_cancel.Left = 225
        btn_cancel.Top = 325
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # ========== Event handlers (after all controls are created) ==========
        def update_points_count(Sender):
            """Calculate resulting number of points based on mode and value"""
            try:
                val = float(edt_value.Text)
                mode_idx = cmb_mode.ItemIndex
                x_range = x_max - x_min
                is_downsampling = False
                
                if mode_idx == 0:  # New Sampling Period
                    if val > 0:
                        new_count = int(x_range / val) + 1
                        lbl_new_points.Caption = f"(≈ {new_count} points)"
                        is_downsampling = val > current_period  # Larger period = lower frequency
                    else:
                        lbl_new_points.Caption = "(invalid)"
                elif mode_idx == 1:  # New Sampling Frequency
                    if val > 0:
                        new_period = 1.0 / val
                        new_count = int(x_range / new_period) + 1
                        lbl_new_points.Caption = f"(≈ {new_count} points)"
                        is_downsampling = new_period > current_period  # Larger period = lower frequency
                    else:
                        lbl_new_points.Caption = "(invalid)"
                elif mode_idx == 2:  # New Number of Points
                    new_count = int(val)
                    if new_count >= 2:
                        lbl_new_points.Caption = f"(= {new_count} points)"
                        is_downsampling = new_count < n_points
                    else:
                        lbl_new_points.Caption = "(min 2)"
                elif mode_idx == 3:  # Resample by Factor
                    if val > 0:
                        new_count = int(n_points * val)
                        lbl_new_points.Caption = f"(≈ {new_count} points)"
                        is_downsampling = val < 1.0  # Factor < 1 means fewer points
                    else:
                        lbl_new_points.Caption = "(invalid)"
                
                # Update button label and ftype visibility based on downsampling detection
                is_down = bool(is_downsampling)  # Convert numpy.bool_ to Python bool
                btn_ok.Caption = "Downsample" if is_down else "Resample"
                lbl_ftype.Visible = is_down
                cb_ftype.Visible = is_down
            except Exception as ex:
                lbl_new_points.Caption = f"(error: {str(ex)})"
                print(f"Error in update_points_count: {str(ex)}")
                btn_ok.Caption = "Resample"
                lbl_ftype.Visible = False
                cb_ftype.Visible = False
        
        def update_default_value(Sender):
            """Update default value and hint based on selected mode"""
            mode_idx = cmb_mode.ItemIndex
            if mode_idx == 0:  # New Sampling Period
                edt_value.Text = f"{current_period:.6g}"
            elif mode_idx == 1:  # New Sampling Frequency
                current_freq = 1.0 / current_period if current_period > 0 else 1.0
                edt_value.Text = f"{current_freq:.6g}"
            elif mode_idx == 2:  # New Number of Points
                edt_value.Text = f"{n_points}"
            elif mode_idx == 3:  # Resample by Factor
                edt_value.Text = "2.0"
            update_points_count(None)
        
        # Assign event handlers
        cmb_mode.OnChange = update_default_value
        edt_value.OnChange = update_points_count
        
        if Form.ShowModal() == 1:
            try:
                # Get parameters
                val = float(edt_value.Text)
                mode_idx = cmb_mode.ItemIndex
                method_idx = cb_method.ItemIndex
                color = int(cb_color.Selected) & 0xFFFFFF
                x_range = x_max - x_min
                
                # Calculate new_period based on mode
                if mode_idx == 0:  # New Sampling Period
                    new_period = val
                    if new_period <= 0:
                        raise ValueError("Period must be greater than 0")
                elif mode_idx == 1:  # New Sampling Frequency
                    if val <= 0:
                        raise ValueError("Frequency must be greater than 0")
                    new_period = 1.0 / val
                elif mode_idx == 2:  # New Number of Points
                    new_n = int(val)
                    if new_n < 2:
                        raise ValueError("Number of points must be at least 2")
                    new_period = x_range / (new_n - 1)
                elif mode_idx == 3:  # Resample by Factor
                    if val <= 0:
                        raise ValueError("Factor must be greater than 0")
                    new_n = int(n_points * val)
                    if new_n < 2:
                        new_n = 2
                    new_period = x_range / (new_n - 1)
                else:
                    raise ValueError("Unrecognized mode")
                
                # Detect if downsampling is needed
                is_downsampling = new_period > current_period
                ftype_idx = cb_ftype.ItemIndex
                
                if is_downsampling and ftype_idx < 2:  # Use decimate with fir or iir
                    # Use scipy.signal.decimate for downsampling
                    # Calculate decimation factor q (must be integer)
                    q = int(round(new_period / current_period))
                    if q < 2:
                        q = 2  # Minimum decimation factor
                    
                    # Determine filter type
                    ftype = 'fir' if ftype_idx == 0 else 'iir'
                    
                    # Apply decimate with selected ftype
                    y_new = decimate(y_orig, q, ftype=ftype)
                    
                    # Generate corresponding X points
                    x_new = x_orig[::q][:len(y_new)]  # Match the length of decimated output
                    
                    # Ensure x_new and y_new have the same length
                    min_len = min(len(x_new), len(y_new))
                    x_new = x_new[:min_len]
                    y_new = y_new[:min_len]
                    
                    method_name = f"decimate(q={q}, ftype={ftype})"
                else:
                    # Generate new X points for upsampling/resampling (or downsampling with interpolation)
                    x_new = np.arange(x_min, x_max + new_period/2, new_period)
                    
                    # Interpolate according to selected method
                    if method_idx == 0:  # np.interp
                        y_new = np.interp(x_new, x_orig, y_orig)
                        method_name = "np.interp"
                    elif method_idx == 1:  # CubicSpline
                        cs = CubicSpline(x_orig, y_orig)
                        y_new = cs(x_new)
                        method_name = "CubicSpline"
                    elif method_idx == 2:  # PchipInterpolator
                        pchip = PchipInterpolator(x_orig, y_orig)
                        y_new = pchip(x_new)
                        method_name = "Pchip"
                    elif method_idx == 3:  # Akima1DInterpolator
                        akima = Akima1DInterpolator(x_orig, y_orig)
                        y_new = akima(x_new)
                        method_name = "Akima"
                    else:
                        raise ValueError("Unrecognized method")
                    
                    # Update is_downsampling to false if using interpolation method
                    if is_downsampling:
                        is_downsampling = False  # Treat as resample since we used interpolation
                
                # Crear nueva serie
                new_points = [Point(float(x), float(y)) for x, y in zip(x_new, y_new)]
                
                new_series = Graph.TPointSeries()
                new_series.PointType = Graph.ptCartesian
                new_series.Points = new_points
                operation_type = "downsample" if is_downsampling else "resample"
                new_series.LegendText = f"{point_series.LegendText} ({operation_type} {method_name})"
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
                
                # show_info(
                #     f"Resample completed.\n\n"
                #     f"Method: {method_name}\n"
                #     f"Period: {new_period:.6g}\n"
                #     f"Puntos originales: {n_points}\n"
                #     f"Puntos nuevos: {len(x_new)}",
                #     "Resample"
                # )
                
            except Exception as e:
                show_error(f"Error resampling: {str(e)}", "Resample")
    
    finally:
        Form.Free()


# Create action for menu
ResampleAction = Graph.CreateAction(
    Caption="Resample...",
    OnExecute=resample_series,
    Hint="Resamples the selected series using interpolation.",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "Resample_sm.png")
)

# Add action to Plugins menu
Graph.AddActionToMainMenu(ResampleAction, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"]) # type: ignore
