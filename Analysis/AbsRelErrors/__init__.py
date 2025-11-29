"""
AbsRelErrors - Plugin para calcular errores absolutos y relativos
Calcula el error de Y respecto a X en la serie seleccionada.
- Error Absoluto: y - x
- Error Relativo: (y - x) / x
"""

import Graph
import vcl
import os

# Importar utilidades comunes
from common import setup_venv, get_selected_point_series, show_error, show_info, get_series_data, Point, create_point_series, add_series_to_graph, safe_color

# Importar numpy
import numpy as np


def compute_errors(Action):
    """
    Muestra un diálogo para calcular errores absolutos y relativos de Y respecto a X.
    """
    # Obtener serie seleccionada
    series, error = get_selected_point_series()
    
    if series is None:
        show_error(error, "Abs/Rel Errors")
        return

    # Obtener datos
    x_vals, y_vals = get_series_data(series)
    
    if not y_vals:
        show_info("La serie seleccionada no contiene puntos.", "Abs/Rel Errors")
        return

    # Convertir a numpy arrays
    x_arr = np.array(x_vals)
    y_arr = np.array(y_vals)
    
    # Calcular errores
    abs_error = y_arr - x_arr
    
    # Para error relativo, evitar división por cero
    with np.errstate(divide='ignore', invalid='ignore'):
        rel_error = np.where(x_arr != 0, (y_arr - x_arr) / x_arr, np.nan)
    
    # Estadísticas de errores
    abs_mean = float(np.nanmean(abs_error))
    abs_std = float(np.nanstd(abs_error))
    abs_max = float(np.nanmax(np.abs(abs_error)))
    
    rel_mean = float(np.nanmean(rel_error)) * 100  # En porcentaje
    rel_std = float(np.nanstd(rel_error)) * 100
    rel_max = float(np.nanmax(np.abs(rel_error))) * 100
    
    n_points = len(y_arr)
    n_valid_rel = int(np.sum(~np.isnan(rel_error)))
    
    # Nombre base de la serie
    series_name = series.LegendText if series.LegendText else "series"

    # Crear formulario
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Abs/Rel Errors - Cálculo de Errores"
        Form.Width = 420
        Form.Height = 380
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        # Título
        lbl_title = vcl.TLabel(Form)
        lbl_title.Parent = Form
        lbl_title.Caption = "Cálculo de Errores Absolutos y Relativos"
        lbl_title.Left = 20
        lbl_title.Top = 15
        lbl_title.Font.Style = {"fsBold"}
        
        # Nombre de la serie
        lbl_series = vcl.TLabel(Form)
        lbl_series.Parent = Form
        lbl_series.Caption = f"Serie: {series_name}"
        lbl_series.Left = 20
        lbl_series.Top = 35
        lbl_series.Font.Color = 0x666666
        
        # Descripción
        lbl_desc = vcl.TLabel(Form)
        lbl_desc.Parent = Form
        lbl_desc.Caption = "Error Absoluto: (Y - X)    |    Error Relativo: (Y - X) / X"
        lbl_desc.Left = 20
        lbl_desc.Top = 55
        lbl_desc.Font.Color = 0x888888
        
        # Panel con estadísticas
        pnl_stats = vcl.TPanel(Form)
        pnl_stats.Parent = Form
        pnl_stats.Left = 20
        pnl_stats.Top = 80
        pnl_stats.Width = 370
        pnl_stats.Height = 150
        pnl_stats.BevelOuter = "bvLowered"
        pnl_stats.Color = 0xFFFFF8
        
        stats_text = (
            f"N Points:              {n_points}\n"
            f"Valid Rel. Points:     {n_valid_rel}\n\n"
            f"─── Error Absoluto ───\n"
            f"Mean:                  {abs_mean:.6g}\n"
            f"Std Dev:               {abs_std:.6g}\n"
            f"Max |error|:           {abs_max:.6g}\n\n"
            f"─── Error Relativo ───\n"
            f"Mean:                  {rel_mean:.4g} %\n"
            f"Std Dev:               {rel_std:.4g} %\n"
            f"Max |error|:           {rel_max:.4g} %"
        )
        
        lbl_stats = vcl.TLabel(Form)
        lbl_stats.Parent = pnl_stats
        lbl_stats.Caption = stats_text
        lbl_stats.Left = 15
        lbl_stats.Top = 10
        lbl_stats.Font.Name = "Consolas"
        
        # Checkboxes para crear series
        chk_abs = vcl.TCheckBox(Form)
        chk_abs.Parent = Form
        chk_abs.Caption = "Crear serie de Error Absoluto"
        chk_abs.Left = 20
        chk_abs.Top = 245
        chk_abs.Width = 250
        chk_abs.Checked = True
        
        chk_rel = vcl.TCheckBox(Form)
        chk_rel.Parent = Form
        chk_rel.Caption = "Crear serie de Error Relativo"
        chk_rel.Left = 20
        chk_rel.Top = 270
        chk_rel.Width = 250
        chk_rel.Checked = True
        
        # Botones
        btn_create = vcl.TButton(Form)
        btn_create.Parent = Form
        btn_create.Caption = "Crear Series"
        btn_create.Left = 170
        btn_create.Top = 310
        btn_create.Width = 100
        btn_create.Height = 30
        
        btn_close = vcl.TButton(Form)
        btn_close.Parent = Form
        btn_close.Caption = "Cerrar"
        btn_close.ModalResult = 2
        btn_close.Cancel = True
        btn_close.Left = 290
        btn_close.Top = 310
        btn_close.Width = 100
        btn_close.Height = 30
        
        def on_create_click(Sender):
            series_created = 0
            
            if chk_abs.Checked:
                # Crear serie de error absoluto
                abs_series = create_point_series(
                    x_vals, abs_error.tolist(),
                    legend=f"{series_name} (abs_error)",
                    color=0x0000AA,  # Rojo
                    line_size=1
                )
                add_series_to_graph(abs_series)
                series_created += 1
            
            if chk_rel.Checked:
                # Crear serie de error relativo (filtrar NaN)
                valid_mask = ~np.isnan(rel_error)
                x_valid = x_arr[valid_mask].tolist()
                rel_valid = rel_error[valid_mask].tolist()
                
                if x_valid:
                    rel_series = create_point_series(
                        x_valid, rel_valid,
                        legend=f"{series_name} (rel_error)",
                        color=0xAA0000,  # Azul
                        line_size=1
                    )
                    add_series_to_graph(rel_series)
                    series_created += 1
                else:
                    show_error("No hay puntos válidos para el error relativo (X=0 en todos los puntos).", "Abs/Rel Errors")
            
            if series_created > 0:
                show_info(f"Se crearon {series_created} serie(s) de error.", "Abs/Rel Errors")
        
        btn_create.OnClick = on_create_click
        
        Form.ShowModal()
    
    finally:
        Form.Free()


# Registrar la acción
Action = Graph.CreateAction(
    Caption="Abs/Rel Errors...", 
    OnExecute=compute_errors, 
    Hint="Calcula errores absolutos y relativos de Y respecto a X",
    IconFile=os.path.join(os.path.dirname(__file__), "AbsRelErrors_sm.png")
)

# Agregar al menú Plugins -> Analysis
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Analysis"])
