# Plugin to import CSV files and convert them to point series
import os
from datetime import datetime
import re

# Import common module (automatically configures venv)
from common import (
    show_error, show_info, safe_color, Point, Graph, vcl
)

import numpy as np

PluginName = "Import CSV"
PluginVersion = "1.1"
PluginDescription = "Imports CSV files and converts each column to a point series."

# Paleta de colores para las series
SERIES_COLORS = [
    0x0000FF,  # Rojo
    0x00AA00,  # Verde
    0xFF0000,  # Azul
    0x00AAAA,  # Amarillo oscuro
    0xAA00AA,  # Magenta
    0xAAAA00,  # Cyan
    0x0055AA,  # Naranja
    0x880088,  # Purple
    0x008800,  # Verde oscuro
    0x000088,  # Rojo oscuro
    0x444444,  # Gris oscuro
    0x008888,  # Oliva
]

# Formatos de datetime comunes
DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",  # 2025-11-03 06:38:54.203
    "%Y-%m-%d %H:%M:%S",     # 2025-11-03 06:38:54
    "%Y/%m/%d %H:%M:%S.%f",  # 2025/11/03 06:38:54.203
    "%Y/%m/%d %H:%M:%S",     # 2025/11/03 06:38:54
    "%d-%m-%Y %H:%M:%S.%f",  # 03-11-2025 06:38:54.203
    "%d-%m-%Y %H:%M:%S",     # 03-11-2025 06:38:54
    "%d/%m/%Y %H:%M:%S.%f",  # 03/11/2025 06:38:54.203
    "%d/%m/%Y %H:%M:%S",     # 03/11/2025 06:38:54
    "%Y-%m-%dT%H:%M:%S.%f",  # ISO format with microseconds
    "%Y-%m-%dT%H:%M:%S",     # ISO format
    "%H:%M:%S.%f",           # Solo hora con microsegundos
    "%H:%M:%S",              # Solo hora
]


def detect_separator(file_path, has_header):
    """
    Automatically detects the CSV file separator.
    """
    separators = [',', ';', '\t', '|']  # Removed simple space due to datetime conflicts
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        # Read the first lines to detect
        lines = []
        for i, line in enumerate(f):
            if i >= 5:  # Read max 5 lines
                break
            lines.append(line.strip())
    
    if not lines:
        return ','
    
    # Contar ocurrencias de cada separador
    best_sep = ','
    best_count = 0
    
    for sep in separators:
        # Count consistent fields across all lines
        counts = [line.count(sep) for line in lines if line]
        if counts and min(counts) > 0 and max(counts) == min(counts):
            if counts[0] > best_count:
                best_count = counts[0]
                best_sep = sep
    
    return best_sep


def try_parse_datetime(value):
    """
    Attempts to parse a value as datetime.
    Returns the datetime object if successful, None if not.
    """
    value = value.strip().strip('"').strip("'")
    
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    
    return None


def try_parse_number(value, separator):
    """
    Attempts to parse a value as a number.
    Returns the float if successful, None if not.
    """
    value = value.strip().strip('"').strip("'")
    
    try:
        return float(value)
    except ValueError:
        pass
    
    # Intentar con reemplazo de coma decimal si el separador no es coma
    if separator != ',':
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            pass
    
    return None


def detect_column_types(file_path, has_header, separator):
    """
    Detects the type of each column: 'numeric', 'datetime', or 'ignore'.
    Also returns headers and the number of columns.
    
    Returns:
        tuple: (headers, column_types, n_cols)
    """
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if not lines:
        raise ValueError("File is empty")
    
    start_idx = 0
    headers = None
    
    if has_header:
        header_line = lines[0]
        headers = [h.strip().strip('"').strip("'") for h in header_line.split(separator)]
        start_idx = 1
    
    if start_idx >= len(lines):
        raise ValueError("No data after header")
    
    # Determine number of columns
    first_data = lines[start_idx].split(separator)
    n_cols = len(first_data)
    
    if headers is None:
        headers = [str(i) for i in range(n_cols)]
    
    # Analyze some rows to determine types
    sample_lines = lines[start_idx:start_idx + min(10, len(lines) - start_idx)]
    
    column_types = []
    for col_idx in range(n_cols):
        numeric_count = 0
        datetime_count = 0
        
        for line in sample_lines:
            parts = line.split(separator)
            if col_idx >= len(parts):
                continue
            
            value = parts[col_idx]
            
            if try_parse_number(value, separator) is not None:
                numeric_count += 1
            elif try_parse_datetime(value) is not None:
                datetime_count += 1
        
        total = len(sample_lines)
        if numeric_count >= total * 0.8:
            column_types.append('numeric')
        elif datetime_count >= total * 0.8:
            column_types.append('datetime')
        else:
            column_types.append('ignore')
    
    return headers, column_types, n_cols


def parse_csv(file_path, has_header, separator, x_col_index):
    """
    Parses the CSV file and returns the data.
    
    Args:
        file_path: Path to file
        has_header: If it has header
        separator: Field separator
        x_col_index: X column index (-1 for none, use 0,1,2...)
    
    Returns:
        tuple: (series_names, x_values, y_columns)
            - series_names: list of series names
            - x_values: array of X values
            - y_columns: list of arrays with Y values for each column
    """
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if not lines:
        raise ValueError("File is empty")
    
    start_idx = 0
    headers = None
    
    if has_header:
        header_line = lines[0]
        headers = [h.strip().strip('"').strip("'") for h in header_line.split(separator)]
        start_idx = 1
    
    # Determine number of columns
    first_data = lines[start_idx].split(separator)
    n_cols = len(first_data)
    
    if headers is None:
        headers = [f"Series {i+1}" for i in range(n_cols)]
    
    # Detect column types
    _, column_types, _ = detect_column_types(file_path, has_header, separator)
    
    # Parse data row by row
    n_rows = len(lines) - start_idx
    
    # Inicializar almacenamiento por columna
    column_data = [[] for _ in range(n_cols)]
    
    for line in lines[start_idx:]:
        parts = line.split(separator)
        
        for col_idx in range(min(len(parts), n_cols)):
            value = parts[col_idx]
            col_type = column_types[col_idx]
            
            if col_type == 'numeric':
                parsed = try_parse_number(value, separator)
                column_data[col_idx].append(parsed if parsed is not None else np.nan)
            elif col_type == 'datetime':
                parsed = try_parse_datetime(value)
                column_data[col_idx].append(parsed)
            else:
                column_data[col_idx].append(None)
    
    # Convertir columnas datetime a segundos relativos
    for col_idx in range(n_cols):
        if column_types[col_idx] == 'datetime':
            dt_values = column_data[col_idx]
            # Find the first valid value as reference
            ref_time = None
            for v in dt_values:
                if v is not None:
                    ref_time = v
                    break
            
            if ref_time is not None:
                # Convertir a segundos desde el inicio
                seconds = []
                for v in dt_values:
                    if v is not None:
                        delta = (v - ref_time).total_seconds()
                        seconds.append(delta)
                    else:
                        seconds.append(np.nan)
                column_data[col_idx] = seconds
            else:
                column_types[col_idx] = 'ignore'
    
    # Convertir a arrays numpy
    for col_idx in range(n_cols):
        if column_types[col_idx] != 'ignore':
            column_data[col_idx] = np.array(column_data[col_idx], dtype=float)
    
    # Determinar valores X
    if x_col_index >= 0 and x_col_index < n_cols and column_types[x_col_index] != 'ignore':
        x_values = column_data[x_col_index]
    else:
        x_values = np.arange(n_rows, dtype=float)
        x_col_index = -1  # Marcar que no hay columna X
    
    # Recopilar columnas Y (excluyendo X y las ignoradas)
    y_columns = []
    series_names = []
    
    for col_idx in range(n_cols):
        if col_idx == x_col_index:
            continue  # Saltar columna X
        if column_types[col_idx] == 'ignore':
            continue  # Skip non-numeric/datetime columns
        
        y_columns.append(column_data[col_idx])
        series_names.append(headers[col_idx])
    
    return series_names, x_values, y_columns


def import_csv(Action):
    """Imports a CSV file and creates point series."""
    
    # Create file selection dialog
    open_dialog = vcl.TOpenDialog(None)
    open_dialog.Title = "Select CSV file"
    open_dialog.Filter = "Archivos CSV (*.csv)|*.csv|Archivos de texto (*.txt)|*.txt|Todos los archivos (*.*)|*.*"
    open_dialog.FilterIndex = 1
    open_dialog.Options = "ofFileMustExist,ofHideReadOnly"
    
    if not open_dialog.Execute():
        return
    
    file_path = open_dialog.FileName
    
    if not os.path.exists(file_path):
        show_error(f"File does not exist:\n{file_path}", "Import CSV")
        return
    
    # Variables to store detected information (use list to allow modification in closure)
    detected_info = [None]  # [0] = {'headers': ..., 'column_types': ..., 'separator': ..., 'n_cols': ...}
    
    # Create configuration form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "CSV Import Configuration"
        Form.Width = 450
        Form.Height = 420
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []
        
        # Show selected file
        lbl_file = vcl.TLabel(Form)
        lbl_file.Parent = Form
        lbl_file.Caption = "File:"
        lbl_file.Left = 20
        lbl_file.Top = 20
        lbl_file.Font.Style = {"fsBold"}
        labels.append(lbl_file)
        
        lbl_filename = vcl.TLabel(Form)
        lbl_filename.Parent = Form
        lbl_filename.Caption = os.path.basename(file_path)
        lbl_filename.Left = 80
        lbl_filename.Top = 20
        lbl_filename.Width = 340
        lbl_filename.Font.Color = 0x666666
        labels.append(lbl_filename)
        
        # Separador visual
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 45
        sep1.Width = 420
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Option: has header
        chk_header = vcl.TCheckBox(Form)
        chk_header.Parent = Form
        chk_header.Caption = "File has header (first row with names)"
        chk_header.Left = 20
        chk_header.Top = 60
        chk_header.Width = 350
        chk_header.Checked = True
        
        # Field separator
        lbl_sep = vcl.TLabel(Form)
        lbl_sep.Parent = Form
        lbl_sep.Caption = "Field separator:"
        lbl_sep.Left = 20
        lbl_sep.Top = 100
        labels.append(lbl_sep)
        
        cb_separator = vcl.TComboBox(Form)
        cb_separator.Parent = Form
        cb_separator.Left = 160
        cb_separator.Top = 97
        cb_separator.Width = 120
        cb_separator.Style = "csDropDownList"
        cb_separator.Items.Add("auto (detect)")
        cb_separator.Items.Add(", (comma)")
        cb_separator.Items.Add("; (semicolon)")
        cb_separator.Items.Add("TAB (tabulator)")
        cb_separator.Items.Add("| (pipe)")
        cb_separator.ItemIndex = 0
        
        # X column selector
        lbl_x_col = vcl.TLabel(Form)
        lbl_x_col.Parent = Form
        lbl_x_col.Caption = "X Column:"
        lbl_x_col.Left = 20
        lbl_x_col.Top = 140
        labels.append(lbl_x_col)
        
        cb_x_column = vcl.TComboBox(Form)
        cb_x_column.Parent = Form
        cb_x_column.Left = 160
        cb_x_column.Top = 137
        cb_x_column.Width = 200
        cb_x_column.Style = "csDropDownList"
        cb_x_column.Items.Add("None (X = 0, 1, 2...)")
        cb_x_column.ItemIndex = 0
        
        # Button to update columns after changing options
        btn_refresh = vcl.TButton(Form)
        btn_refresh.Parent = Form
        btn_refresh.Caption = "Detect columns"
        btn_refresh.Left = 20
        btn_refresh.Top = 175
        btn_refresh.Width = 130
        btn_refresh.Height = 25
        
        # Status label
        lbl_status = vcl.TLabel(Form)
        lbl_status.Parent = Form
        lbl_status.Caption = ""
        lbl_status.Left = 160
        lbl_status.Top = 180
        lbl_status.Font.Color = 0x008800
        labels.append(lbl_status)
        
        def refresh_columns(Sender):
            """Detects and updates the list of available columns."""
            try:
                has_header = chk_header.Checked
                
                # Determinar separador
                sep_idx = cb_separator.ItemIndex
                if sep_idx == 0:
                    separator = detect_separator(file_path, has_header)
                elif sep_idx == 1:
                    separator = ','
                elif sep_idx == 2:
                    separator = ';'
                elif sep_idx == 3:
                    separator = '\t'
                elif sep_idx == 4:
                    separator = '|'
                else:
                    separator = ','
                
                # Detectar columnas
                headers, column_types, n_cols = detect_column_types(file_path, has_header, separator)
                
                # Update X column combo
                cb_x_column.Items.Clear()
                cb_x_column.Items.Add("None (X = 0, 1, 2...)")
                
                usable_cols = 0
                for i, (header, col_type) in enumerate(zip(headers, column_types)):
                    if col_type != 'ignore':
                        type_indicator = " [datetime→s]" if col_type == 'datetime' else ""
                        cb_x_column.Items.Add(f"{header}{type_indicator}")
                        usable_cols += 1
                
                cb_x_column.ItemIndex = 0
                
                ignored = sum(1 for t in column_types if t == 'ignore')
                status_msg = f"{usable_cols} usable columns"
                if ignored > 0:
                    status_msg += f", {ignored} ignored"
                lbl_status.Caption = status_msg
                lbl_status.Font.Color = 0x008800
                
                # Save information for later use (in local variable)
                detected_info[0] = {
                    'headers': headers,
                    'column_types': column_types,
                    'separator': separator,
                    'n_cols': n_cols
                }
                
            except Exception as e:
                lbl_status.Caption = f"Error: {str(e)}"
                lbl_status.Font.Color = 0x0000AA
                detected_info[0] = None
        
        btn_refresh.OnClick = refresh_columns
        
        # Help panel
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 20
        help_panel.Top = 215
        help_panel.Width = 400
        help_panel.Height = 110
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0
        
        lbl_help_title = vcl.TLabel(Form)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Information:"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)
        
        help_text = (
            "• Each numeric column will be converted to a series\n"
            "• Datetime columns are converted to seconds (from t=0)\n"
            "• Non-numeric text columns will be ignored\n"
            "• Use 'Detect columns' after changing options\n"
            "• Series will be plotted with different colors"
        )
        
        lbl_help = vcl.TLabel(Form)
        lbl_help.Parent = help_panel
        lbl_help.Caption = help_text
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Import"
        btn_ok.ModalResult = 1
        btn_ok.Default = True
        btn_ok.Left = 120
        btn_ok.Top = 345
        btn_ok.Width = 100
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        btn_cancel.Left = 240
        btn_cancel.Top = 345
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # Detectar columnas inicialmente
        refresh_columns(None)
        
        if Form.ShowModal() == 1:
            try:
                has_header = chk_header.Checked
                
                # Get saved information
                tag_data = detected_info[0]
                if not tag_data:
                    raise ValueError("Press 'Detect columns' first")
                
                separator = tag_data['separator']
                headers = tag_data['headers']
                column_types = tag_data['column_types']
                
                # Determine X column index
                x_selection = cb_x_column.ItemIndex
                if x_selection == 0:
                    x_col_index = -1  # Ninguna
                else:
                    # Find the real index of the selected column
                    # (contando solo las columnas no ignoradas)
                    usable_idx = 0
                    x_col_index = -1
                    for i, col_type in enumerate(column_types):
                        if col_type != 'ignore':
                            usable_idx += 1
                            if usable_idx == x_selection:
                                x_col_index = i
                                break
                
                # Parsear CSV
                series_names, x_values, y_columns = parse_csv(
                    file_path, has_header, separator, x_col_index
                )
                
                if not y_columns:
                    raise ValueError("No data columns found to import")
                
                # Crear series
                n_series = len(y_columns)
                
                for i, (y_vals, series_name) in enumerate(zip(y_columns, series_names)):
                    # Determinar color
                    color = SERIES_COLORS[i % len(SERIES_COLORS)]
                    
                    # Crear puntos (filtrar NaN)
                    points = []
                    for x, y in zip(x_values, y_vals):
                        if not (np.isnan(x) or np.isnan(y)):
                            points.append(Point(float(x), float(y)))
                    
                    if not points:
                        continue  # Skip empty series
                    
                    # Crear serie
                    new_series = Graph.TPointSeries()
                    new_series.PointType = Graph.ptCartesian
                    new_series.Points = points
                    new_series.LegendText = series_name
                    new_series.Size = 0  # Sin marcador visible
                    new_series.Style = 0  # Circle
                    new_series.LineSize = 1
                    new_series.ShowLabels = False
                    
                    # Aplicar color
                    color_val = safe_color(color)
                    new_series.FillColor = color_val
                    new_series.FrameColor = color_val
                    new_series.LineColor = color_val
                    
                    Graph.FunctionList.append(new_series)
                
                Graph.Update()
                
                show_info(
                    f"Import completed.\n\n"
                    f"File: {os.path.basename(file_path)}\n"
                    f"Series imported: {n_series}\n"
                    f"Points per series: {len(x_values)}",
                    "Import CSV"
                )
                
            except Exception as e:
                show_error(f"Error importing: {str(e)}", "Import CSV")
    
    finally:
        Form.Free()


# Create action for menu
ImportCSVAction = Graph.CreateAction(
    Caption="Import CSV...",
    OnExecute=import_csv,
    Hint="Imports CSV files and converts each column to a point series.",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "CSV_sm.png")
)

# Add action to Plugins menu
Graph.AddActionToMainMenu(ImportCSVAction, TopMenu="Plugins", SubMenus=["Graphîa", "Import/Export"])
