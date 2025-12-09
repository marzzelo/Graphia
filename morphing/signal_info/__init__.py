
import Graph
import vcl # type: ignore
import os
import sys

# Import common utilities
# This also configures the virtual environment for numpy
from common import (
    setup_venv, get_selected_point_series, show_error, show_info, 
    get_series_data, get_function_info
)

# Import numpy for statistical calculations
import numpy as np


def add_info_functions(x_min, x_max, y_min, y_max, y_mean, y_median, y_std):
    """Adds constant functions to the graph to visualize statistics."""
    
    # Colors for lines (in BGR format for VCL)
    colors = {
        'ymin': 0x0000AA,      # Rojo oscuro
        'ymax': 0x00AA00,      # Verde
        'mean': 0xAA0000,      # Azul
        'median': 0xAA00AA,    # Magenta
        'std_plus': 0x888888,  # Gris
        'std_minus': 0x888888, # Gris
    }
    
    # Lista de funciones a agregar: (valor, label, color)
    functions_to_add = [
        (y_min, f"(info) Ymin = {y_min:.4f}", colors['ymin']),
        (y_max, f"(info) Ymax = {y_max:.4f}", colors['ymax']),
        (y_mean, f"(info) Mean(Y) = {y_mean:.4f}", colors['mean']),
        (y_median, f"(info) Median(Y) = {y_median:.4f}", colors['median']),
        (y_median + y_std, f"(info) +std = {(y_median + y_std):.4f}", colors['std_plus']),
        (y_median - y_std, f"(info) -std = {(y_median - y_std):.4f}", colors['std_minus']),
    ]
    
    for value, label, color in functions_to_add:
        # TStdFunc takes equation as constructor argument
        func = Graph.TStdFunc(f"{value:.4f}")
        func.From = x_min
        func.To = x_max
        func.LegendText = label
        func.Color = color
        func.Size = 2
        func.Style = 2  # Dotted line (psDot)
        Graph.FunctionList.append(func)
    
    Graph.Redraw()


def clear_info_functions():
    """Removes all functions containing '(info)' in the label."""
    # Collect indices of elements to remove (from highest to lowest to avoid affecting indices)
    to_remove = []
    for i in range(len(Graph.FunctionList)):
        elem = Graph.FunctionList[i]
        if hasattr(elem, 'LegendText') and elem.LegendText and "(info)" in elem.LegendText: # type: ignore
            to_remove.append(i)
    
    # Remove from highest to lowest index
    for i in reversed(to_remove):
        del Graph.FunctionList[i]
    
    Graph.Update()
    return len(to_remove)


def show_signal_statistics(Action):
    """
    Shows statistics for the selected point series or function.
    """
    selected = Graph.Selected
    
    if selected is None:
        show_error("No item selected in the function panel.", "Signal Info")
        return
    
    # Check if it's a TStdFunc
    if isinstance(selected, Graph.TStdFunc):
        show_function_info(selected)
        return
    
    # Check if it's a TPointSeries
    if not isinstance(selected, Graph.TPointSeries):
        type_name = type(selected).__name__
        show_error(f"The selected item is not a point series or function.\nCurrent type: {type_name}", "Signal Info")
        return
    
    series = selected

    # Obtener datos
    x_vals, y_vals = get_series_data(series)
    
    if not y_vals:
        show_info("The selected series has no points.", "Signal Info")
        return

    # Convert to numpy arrays for efficient calculations
    y_arr = np.array(y_vals)
    x_arr = np.array(x_vals)

    # Calculate statistics
    x_min = float(np.min(x_arr))
    x_max = float(np.max(x_arr))
    y_min = float(np.min(y_arr))
    y_max = float(np.max(y_arr))
    y_mean = float(np.mean(y_arr))
    y_median = float(np.median(y_arr))
    y_std = float(np.std(y_arr))
    y_rms = float(np.sqrt(np.mean(y_arr**2)))
    n_points = len(y_arr)
    
    # Calculate sampling period and frequency
    if n_points > 1:
        dx_arr = np.diff(x_arr)
        ts = float(np.mean(dx_arr))  # Average sampling period
        fs = 1.0 / ts if ts > 0 else 0.0  # Sampling frequency
    else:
        ts = 0.0
        fs = 0.0

    # Create form with statistics and buttons
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Signal Info - Statistics"
        Form.Width = 380
        Form.Height = 470
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []
        
        # Title
        lbl_title = vcl.TLabel(Form)
        lbl_title.Parent = Form
        lbl_title.Caption = "Statistics for Selected Series"
        lbl_title.Left = 20
        lbl_title.Top = 15
        lbl_title.Font.Style = {"fsBold"}
        labels.append(lbl_title)
        
        # Series name
        if series.LegendText:
            lbl_series = vcl.TLabel(Form)
            lbl_series.Parent = Form
            lbl_series.Caption = f"Series: {series.LegendText}"
            lbl_series.Left = 20
            lbl_series.Top = 35
            lbl_series.Font.Color = 0x666666
            labels.append(lbl_series)
        
        # Statistics panel
        pnl_stats = vcl.TPanel(Form)
        pnl_stats.Parent = Form
        pnl_stats.Left = 20
        pnl_stats.Top = 60
        pnl_stats.Width = 330
        pnl_stats.Height = 230
        pnl_stats.BevelOuter = "bvLowered"
        pnl_stats.Color = 0xFFFFF8
        
        stats_text = (
            f"N Points:        {n_points}\n"
            f"Ts [s]:          {ts:.6g}\n"
            f"fs [Hz]:         {fs:.6g}\n\n"
            f"X Min:           {x_min:.6g}\n"
            f"X Max:           {x_max:.6g}\n\n"
            f"Y Min:           {y_min:.6g}\n"
            f"Y Max:           {y_max:.6g}\n\n"
            f"Mean (Y):        {y_mean:.6g}\n"
            f"Median (Y):      {y_median:.6g}\n"
            f"Std Dev (Y):     {y_std:.6g}\n"
            f"RMS (Y):         {y_rms:.6g}"
        )
        
        lbl_stats = vcl.TLabel(Form)
        lbl_stats.Parent = pnl_stats
        lbl_stats.Caption = stats_text
        lbl_stats.Left = 15
        lbl_stats.Top = 10
        lbl_stats.Font.Name = "Consolas"
        labels.append(lbl_stats)
        
        # Section to set new mean
        lbl_new_mean = vcl.TLabel(Form)
        lbl_new_mean.Parent = Form
        lbl_new_mean.Caption = "New Mean:"
        lbl_new_mean.Left = 20
        lbl_new_mean.Top = 305
        
        edt_new_mean = vcl.TEdit(Form)
        edt_new_mean.Parent = Form
        edt_new_mean.Left = 100
        edt_new_mean.Top = 302
        edt_new_mean.Width = 100
        edt_new_mean.Text = f"{y_mean:.6g}"
        
        btn_set_mean = vcl.TButton(Form)
        btn_set_mean.Parent = Form
        btn_set_mean.Caption = "Set"
        btn_set_mean.Left = 210
        btn_set_mean.Top = 300
        btn_set_mean.Width = 60
        btn_set_mean.Height = 25
        
        # Section to set new median
        lbl_new_median = vcl.TLabel(Form)
        lbl_new_median.Parent = Form
        lbl_new_median.Caption = "New Median:"
        lbl_new_median.Left = 20
        lbl_new_median.Top = 335
        
        edt_new_median = vcl.TEdit(Form)
        edt_new_median.Parent = Form
        edt_new_median.Left = 100
        edt_new_median.Top = 332
        edt_new_median.Width = 100
        edt_new_median.Text = f"{y_median:.6g}"
        
        btn_set_median = vcl.TButton(Form)
        btn_set_median.Parent = Form
        btn_set_median.Caption = "Set"
        btn_set_median.Left = 210
        btn_set_median.Top = 330
        btn_set_median.Width = 60
        btn_set_median.Height = 25
        
        # Botones
        btn_visualize = vcl.TButton(Form)
        btn_visualize.Parent = Form
        btn_visualize.Caption = "Visualize"
        btn_visualize.Left = 20
        btn_visualize.Top = 380
        btn_visualize.Width = 100
        btn_visualize.Height = 30
        
        btn_clear = vcl.TButton(Form)
        btn_clear.Parent = Form
        btn_clear.Caption = "Clear Info"
        btn_clear.Left = 135
        btn_clear.Top = 380
        btn_clear.Width = 100
        btn_clear.Height = 30
        
        btn_close = vcl.TButton(Form)
        btn_close.Parent = Form
        btn_close.Caption = "Close"
        btn_close.ModalResult = 2
        btn_close.Cancel = True
        btn_close.Left = 250
        btn_close.Top = 380
        btn_close.Width = 100
        btn_close.Height = 30
        
        def on_visualize_click(Sender):
            add_info_functions(x_min, x_max, y_min, y_max, y_mean, y_median, y_std)
        
        def on_clear_click(Sender):
            count = clear_info_functions()
        
        def on_set_mean_click(Sender):
            try:
                new_mean = float(edt_new_mean.Text)
            except ValueError:
                show_error("Please enter a valid numeric value.", "Set Mean")
                return
            
            # Calcular el desplazamiento necesario: -mean_actual + new_mean
            offset = -y_mean + new_mean
            
            # Crear nueva lista de puntos con Y desplazado
            from common import Point
            new_points = [Point(p.x, p.y + offset) for p in series.Points]
            series.Points = new_points
            
            # Update field to reflect new value
            edt_new_mean.Text = f"{new_mean:.6g}"
            
            Graph.Redraw()
        
        def on_set_median_click(Sender):
            try:
                new_median = float(edt_new_median.Text)
            except ValueError:
                show_error("Please enter a valid numeric value.", "Set Median")
                return
            
            # Calcular el desplazamiento necesario: -median_actual + new_median
            offset = -y_median + new_median
            
            # Crear nueva lista de puntos con Y desplazado
            from common import Point
            new_points = [Point(p.x, p.y + offset) for p in series.Points]
            series.Points = new_points
            
            # Update field to reflect new value
            edt_new_median.Text = f"{new_median:.6g}"
            
            Graph.Redraw()
        
        btn_visualize.OnClick = on_visualize_click
        btn_clear.OnClick = on_clear_click
        btn_set_mean.OnClick = on_set_mean_click
        btn_set_median.OnClick = on_set_median_click
        
        Form.ShowModal()
    
    finally:
        Form.Free()


def show_function_info(func):
    """
    Shows information for the selected TStdFunc.
    """
    # Get function info using common helper
    info = get_function_info(func)
    
    # Create form with function info
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Signal Info - Function"
        Form.Width = 380
        Form.Height = 280
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        # Title
        lbl_title = vcl.TLabel(Form)
        lbl_title.Parent = Form
        lbl_title.Caption = "Function Information"
        lbl_title.Left = 20
        lbl_title.Top = 15
        lbl_title.Font.Style = {"fsBold"}
        
        # Function name/legend
        legend_text = func.LegendText if hasattr(func, 'LegendText') and func.LegendText else "Unnamed"
        lbl_legend = vcl.TLabel(Form)
        lbl_legend.Parent = Form
        lbl_legend.Caption = f"Legend: {legend_text}"
        lbl_legend.Left = 20
        lbl_legend.Top = 35
        lbl_legend.Font.Color = 0x666666
        
        # Info panel
        pnl_info = vcl.TPanel(Form)
        pnl_info.Parent = Form
        pnl_info.Left = 20
        pnl_info.Top = 60
        pnl_info.Width = 330
        pnl_info.Height = 140
        pnl_info.BevelOuter = "bvLowered"
        pnl_info.Color = 0xFFFFF8
        
        # Calculate domain size
        x_from = info['x_from']
        x_to = info['x_to']
        x_range = x_to - x_from
        
        info_text = (
            f"Equation:    {info['text']}\n\n"
            f"Domain From: {x_from:.6g}\n"
            f"Domain To:   {x_to:.6g}\n"
            f"Domain Size: {x_range:.6g}\n\n"
            f"Type:        TStdFunc"
        )
        
        lbl_info = vcl.TLabel(Form)
        lbl_info.Parent = pnl_info
        lbl_info.Caption = info_text
        lbl_info.Left = 15
        lbl_info.Top = 10
        lbl_info.Font.Name = "Consolas"
        
        # Close button
        btn_close = vcl.TButton(Form)
        btn_close.Parent = Form
        btn_close.Caption = "Close"
        btn_close.ModalResult = 2
        btn_close.Cancel = True
        btn_close.Left = 250
        btn_close.Top = 210
        btn_close.Width = 100
        btn_close.Height = 30
        
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="Signal Info...", 
    OnExecute=show_signal_statistics, 
    Hint="Shows detailed statistics for the selected series (Min, Max, Mean, StdDev...)",
    IconFile=os.path.join(os.path.dirname(__file__), "SignalInfo_sm.png")
)

# Add to Plugins -> Morphing menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"]) # type: ignore
