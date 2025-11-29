
import Graph
import vcl # type: ignore
import os
import sys

# Import common utilities
# This also configures the virtual environment for numpy
from common import setup_venv, get_selected_point_series, show_error, show_info, get_series_data

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
        (y_min, f"(info) Ymin = {y_min:.4g}", colors['ymin']),
        (y_max, f"(info) Ymax = {y_max:.4g}", colors['ymax']),
        (y_mean, f"(info) Mean(Y) = {y_mean:.4g}", colors['mean']),
        (y_median, f"(info) Median(Y) = {y_median:.4g}", colors['median']),
        (y_median + y_std, f"(info) +std = {y_median + y_std:.4g}", colors['std_plus']),
        (y_median - y_std, f"(info) -std = {y_median - y_std:.4g}", colors['std_minus']),
    ]
    
    for value, label, color in functions_to_add:
        # TStdFunc takes equation as constructor argument
        func = Graph.TStdFunc(str(value))
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
    Shows statistics for the selected series.
    """
    # Obtener serie seleccionada
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "Signal Info")
        return

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

    # Create form with statistics and buttons
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Signal Info - Statistics"
        Form.Width = 380
        Form.Height = 410
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
        pnl_stats.Height = 200
        pnl_stats.BevelOuter = "bvLowered"
        pnl_stats.Color = 0xFFFFF8
        
        stats_text = (
            f"N Points:        {n_points}\n\n"
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
        lbl_new_mean.Top = 275
        
        edt_new_mean = vcl.TEdit(Form)
        edt_new_mean.Parent = Form
        edt_new_mean.Left = 100
        edt_new_mean.Top = 272
        edt_new_mean.Width = 100
        edt_new_mean.Text = "0.0"
        
        btn_set_mean = vcl.TButton(Form)
        btn_set_mean.Parent = Form
        btn_set_mean.Caption = "Set"
        btn_set_mean.Left = 210
        btn_set_mean.Top = 270
        btn_set_mean.Width = 60
        btn_set_mean.Height = 25
        
        # Botones
        btn_visualize = vcl.TButton(Form)
        btn_visualize.Parent = Form
        btn_visualize.Caption = "Visualize"
        btn_visualize.Left = 20
        btn_visualize.Top = 320
        btn_visualize.Width = 100
        btn_visualize.Height = 30
        
        btn_clear = vcl.TButton(Form)
        btn_clear.Parent = Form
        btn_clear.Caption = "Clear Info"
        btn_clear.Left = 135
        btn_clear.Top = 320
        btn_clear.Width = 100
        btn_clear.Height = 30
        
        btn_close = vcl.TButton(Form)
        btn_close.Parent = Form
        btn_close.Caption = "Close"
        btn_close.ModalResult = 2
        btn_close.Cancel = True
        btn_close.Left = 250
        btn_close.Top = 320
        btn_close.Width = 100
        btn_close.Height = 30
        
        def on_visualize_click(Sender):
            add_info_functions(x_min, x_max, y_min, y_max, y_mean, y_median, y_std)
            # show_info("Added 6 reference functions to graph.", "Visualize")
        
        def on_clear_click(Sender):
            count = clear_info_functions()
            # show_info(f"Removed {count} info functions.", "Clear Info")
        
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
            
            Graph.Redraw()
            # show_info(f"Media desplazada de {y_mean:.6g} a {new_mean:.6g}\nOffset aplicado: {offset:.6g}", "Set Mean")
        
        btn_visualize.OnClick = on_visualize_click
        btn_clear.OnClick = on_clear_click
        btn_set_mean.OnClick = on_set_mean_click
        
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
