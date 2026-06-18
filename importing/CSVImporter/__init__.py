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
PluginVersion = "1.3"
PluginDescription = "Imports CSV files and converts each column to a point series."

# NaN handling options
NAN_HANDLING_DELETE_ROW = 0
NAN_HANDLING_FILL_MEDIAN = 1

# Decimation methods
DECIMATE_FIRST = 0
DECIMATE_MEAN = 1
DECIMATE_MEDIAN = 2
DECIMATE_MIN = 3
DECIMATE_MAX = 4

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


def detect_separator(file_path, has_header, skip_rows=0):
    """
    Automatically detects the CSV file separator.
    """
    separators = [',', ';', '\t', '|']  # Removed simple space due to datetime conflicts

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        all_lines = []
        for i, line in enumerate(f):
            if i >= 6 + skip_rows:  # Read max 6 lines to have enough data after skipping header
                break
            all_lines.append(line.rstrip('\n\r'))

    if not all_lines:
        return ','

    all_lines = all_lines[skip_rows:]
    if not all_lines:
        return ','

    # Skip the header line for consistency checks — header column count can differ from data rows
    lines = all_lines[1:] if has_header and len(all_lines) > 1 else all_lines

    # Contar ocurrencias de cada separador
    best_sep = ','
    best_count = 0

    for sep in separators:
        # Count consistent fields across all data lines
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


def detect_column_types(file_path, has_header, separator, skip_rows=0):
    """
    Detects the type of each column: 'numeric', 'datetime', or 'ignore'.
    Also returns headers and the number of columns.

    Returns:
        tuple: (headers, column_types, n_cols)
    """
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = [line.rstrip('\n\r') for line in f if line.strip()]

    if not lines:
        raise ValueError("File is empty")

    lines = lines[skip_rows:]
    if not lines:
        raise ValueError("No data after skipped rows")

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
        empty_count = 0

        for line in sample_lines:
            parts = line.split(separator)
            if col_idx >= len(parts):
                continue

            value = parts[col_idx].strip().strip('"').strip("'")

            # Skip empty values - they don't determine the type
            if not value:
                empty_count += 1
                continue

            if try_parse_number(value, separator) is not None:
                numeric_count += 1
            elif try_parse_datetime(value) is not None:
                datetime_count += 1

        # Calculate based on non-empty values only
        non_empty_total = len(sample_lines) - empty_count
        if non_empty_total > 0:
            if numeric_count >= non_empty_total * 0.8:
                column_types.append('numeric')
            elif datetime_count >= non_empty_total * 0.8:
                column_types.append('datetime')
            else:
                column_types.append('ignore')
        else:
            # All values are empty - treat as ignore
            column_types.append('ignore')

    return headers, column_types, n_cols


def fill_nan_with_neighbor_median(arr, window=3):
    """
    Fills NaN values with the median of neighboring values.

    Args:
        arr: numpy array with potential NaN values
        window: number of neighbors on each side to consider

    Returns:
        numpy array with NaN values filled
    """
    result = arr.copy()
    nan_indices = np.where(np.isnan(result))[0]

    for idx in nan_indices:
        # Get neighbors within window
        start = max(0, idx - window)
        end = min(len(result), idx + window + 1)
        neighbors = result[start:end]

        # Filter out NaN from neighbors
        valid_neighbors = neighbors[~np.isnan(neighbors)]

        if len(valid_neighbors) > 0:
            result[idx] = np.median(valid_neighbors)
        else:
            # If no valid neighbors, leave as NaN (will be handled later)
            pass

    return result


def _aggregate_group(buf, method):
    """Compute one value from a group buffer using the specified decimation method."""
    if not buf:
        return np.nan
    if method == DECIMATE_FIRST:
        v = buf[0]
        if v is None:
            return np.nan
        try:
            fv = float(v)
            return np.nan if np.isnan(fv) else fv
        except (TypeError, ValueError):
            return np.nan
    valid = np.array(
        [float(v) for v in buf if v is not None and not np.isnan(float(v))],
        dtype=float
    )
    if len(valid) == 0:
        return np.nan
    if method == DECIMATE_MEAN:
        return float(np.mean(valid))
    if method == DECIMATE_MEDIAN:
        return float(np.median(valid))
    if method == DECIMATE_MIN:
        return float(np.min(valid))
    if method == DECIMATE_MAX:
        return float(np.max(valid))
    return np.nan


def parse_csv_decimated(file_path, has_header, separator, x_col_index,
                        selected_columns=None, nan_handling=NAN_HANDLING_DELETE_ROW,
                        start_row=0, row_limit=None, skip_rows=0,
                        stride=10, decimate_method=DECIMATE_FIRST):
    """
    Memory-efficient CSV parser with decimation.
    Reads `stride` rows at a time, never holds the full file in RAM.
    One aggregated point is emitted per group.
    """
    headers_det, column_types, n_cols = detect_column_types(
        file_path, has_header, separator, skip_rows)

    if selected_columns is None:
        columns_to_use = [i for i in range(n_cols) if column_types[i] != 'ignore']
    else:
        columns_to_use = [i for i in selected_columns if i < n_cols and column_types[i] != 'ignore']

    eff_x = (x_col_index
             if (0 <= x_col_index < n_cols and column_types[x_col_index] != 'ignore')
             else -1)

    # Union of selected columns + x column
    cols_to_process = sorted(set(columns_to_use) | ({eff_x} if eff_x >= 0 else set()))

    dt_refs = {}
    col_bufs = {c: [] for c in cols_to_process}
    col_out = {c: [] for c in cols_to_process}
    x_idx_out = []  # row indices used when x is positional

    rows_in_window = 0
    rows_processed = 0
    group_start_row = 0

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        for _ in range(skip_rows):
            f.readline()
        if has_header:
            f.readline()

        data_row = 0
        for raw_line in f:
            line = raw_line.rstrip('\n\r')
            if not line.strip():
                continue
            data_row += 1
            if data_row <= start_row:
                continue
            if row_limit is not None and rows_processed >= row_limit:
                break

            parts = line.split(separator)
            for c in cols_to_process:
                if c >= len(parts):
                    col_bufs[c].append(np.nan)
                    continue
                val = parts[c]
                ct = column_types[c]
                if ct == 'numeric':
                    parsed = try_parse_number(val, separator)
                    col_bufs[c].append(parsed if parsed is not None else np.nan)
                elif ct == 'datetime':
                    parsed = try_parse_datetime(val)
                    if parsed is not None:
                        if c not in dt_refs:
                            dt_refs[c] = parsed
                        col_bufs[c].append((parsed - dt_refs[c]).total_seconds())
                    else:
                        col_bufs[c].append(np.nan)
                else:
                    col_bufs[c].append(None)

            rows_processed += 1
            rows_in_window += 1

            if rows_in_window >= stride:
                if eff_x < 0:
                    x_idx_out.append(float(group_start_row))
                for c in cols_to_process:
                    col_out[c].append(_aggregate_group(col_bufs[c], decimate_method))
                    col_bufs[c] = []
                group_start_row = rows_processed
                rows_in_window = 0

        # Flush remaining partial group
        if rows_in_window > 0:
            if eff_x < 0:
                x_idx_out.append(float(group_start_row))
            for c in cols_to_process:
                col_out[c].append(_aggregate_group(col_bufs[c], decimate_method))

    x_values = (np.array(col_out[eff_x], dtype=float)
                if eff_x >= 0
                else np.array(x_idx_out, dtype=float))

    series_names = []
    y_columns = []
    for c in columns_to_use:
        if c == eff_x:
            continue
        series_names.append(headers_det[c])
        y_columns.append(np.array(col_out[c], dtype=float))

    if nan_handling == NAN_HANDLING_FILL_MEDIAN:
        y_columns = [fill_nan_with_neighbor_median(yc) for yc in y_columns]
    elif nan_handling == NAN_HANDLING_DELETE_ROW and y_columns:
        valid_mask = ~np.isnan(x_values)
        for yc in y_columns:
            valid_mask &= ~np.isnan(yc)
        x_values = x_values[valid_mask]
        y_columns = [yc[valid_mask] for yc in y_columns]

    return series_names, x_values, y_columns, len(x_values)


def parse_csv(file_path, has_header, separator, x_col_index, selected_columns=None,
              nan_handling=NAN_HANDLING_DELETE_ROW, start_row=0, row_limit=None,
              skip_rows=0):
    """
    Parses the CSV file and returns the data.

    Args:
        file_path: Path to file
        has_header: If it has header
        separator: Field separator
        x_col_index: X column index (-1 for none, use 0,1,2...)
        selected_columns: List of column indices to import (None = all)
        nan_handling: How to handle NaN values (NAN_HANDLING_DELETE_ROW or NAN_HANDLING_FILL_MEDIAN)
        start_row: First data row to import (0-based, after header if present)
        row_limit: Maximum number of rows to import (None = all)

    Returns:
        tuple: (series_names, x_values, y_columns)
            - series_names: list of series names
            - x_values: array of X values
            - y_columns: list of arrays with Y values for each column
    """
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = [line.rstrip('\n\r') for line in f if line.strip()]

    if not lines:
        raise ValueError("File is empty")

    lines = lines[skip_rows:]
    if not lines:
        raise ValueError("No data after skipped rows")

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
    _, column_types, _ = detect_column_types(file_path, has_header, separator, skip_rows)

    # Apply start_row and row_limit to data lines
    data_lines = lines[start_idx:]
    if start_row > 0:
        data_lines = data_lines[start_row:]
    if row_limit is not None and row_limit > 0:
        data_lines = data_lines[:row_limit]

    # Parse data row by row
    n_rows = len(data_lines)

    # Inicializar almacenamiento por columna
    column_data = [[] for _ in range(n_cols)]

    for line in data_lines:
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

    # Handle NaN values based on nan_handling option
    if nan_handling == NAN_HANDLING_FILL_MEDIAN:
        # Fill NaN with median of neighbors for each column
        for col_idx in range(n_cols):
            if column_types[col_idx] != 'ignore':
                column_data[col_idx] = fill_nan_with_neighbor_median(column_data[col_idx])

    # Determinar valores X
    if x_col_index >= 0 and x_col_index < n_cols and column_types[x_col_index] != 'ignore':
        x_values = column_data[x_col_index]
    else:
        x_values = np.arange(n_rows, dtype=float)
        x_col_index = -1  # Marcar que no hay columna X

    # Determine which columns to use based on selected_columns
    if selected_columns is None:
        # Use all non-ignored columns except X
        columns_to_use = [i for i in range(n_cols) if column_types[i] != 'ignore']
    else:
        columns_to_use = [i for i in selected_columns if i < n_cols and column_types[i] != 'ignore']

    # Recopilar columnas Y (excluyendo X y las ignoradas)
    y_columns = []
    series_names = []

    for col_idx in columns_to_use:
        if col_idx == x_col_index:
            continue  # Saltar columna X

        y_columns.append(column_data[col_idx])
        series_names.append(headers[col_idx])

    # Handle NaN by deleting rows if that option is selected
    if nan_handling == NAN_HANDLING_DELETE_ROW and y_columns:
        # Find rows where any value is NaN
        valid_mask = ~np.isnan(x_values)
        for y_col in y_columns:
            valid_mask &= ~np.isnan(y_col)

        # Apply mask
        x_values = x_values[valid_mask]
        y_columns = [y_col[valid_mask] for y_col in y_columns]
        n_rows = len(x_values)

    return series_names, x_values, y_columns, n_rows


def count_data_rows(file_path, has_header, skip_rows=0):
    """Count the total number of data rows in the file."""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = [line.strip() for line in f if line.strip()]

    start_idx = skip_rows + (1 if has_header else 0)
    return max(0, len(lines) - start_idx)


def import_csv(Action):
    """Imports one or more CSV files and creates point series."""

    # Create file selection dialog (multi-select)
    open_dialog = vcl.TOpenDialog(None)
    open_dialog.Title = "Select CSV file(s)"
    open_dialog.Filter = "Archivos CSV (*.csv)|*.csv|Archivos de texto (*.txt)|*.txt|Todos los archivos (*.*)|*.*"
    open_dialog.FilterIndex = 1
    open_dialog.Options = "ofFileMustExist,ofHideReadOnly,ofAllowMultiSelect"

    if not open_dialog.Execute():
        return

    # Collect file list (multi-select or single)
    try:
        file_paths = [open_dialog.Files[i] for i in range(open_dialog.Files.Count)]
        if not file_paths:
            file_paths = [open_dialog.FileName]
    except Exception:
        file_paths = [open_dialog.FileName]

    file_paths = [p for p in file_paths if p and os.path.exists(p)]
    if not file_paths:
        show_error("No valid files selected.", "Import CSV")
        return

    # Use first file for column detection / UI
    file_path = file_paths[0]

    # Variables to store detected information (use list to allow modification in closure)
    detected_info = [None]  # [0] = {'headers': ..., 'column_types': ..., 'separator': ..., 'n_cols': ...}
    column_checkboxes = []  # List of (checkbox, column_index) tuples

    # Create configuration form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "CSV Import Configuration"
        Form.Width = 520
        Form.Height = 780
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"

        labels = []

        # Show selected file(s)
        lbl_file = vcl.TLabel(Form)
        lbl_file.Parent = Form
        lbl_file.Caption = "File(s):"
        lbl_file.Left = 20
        lbl_file.Top = 15
        lbl_file.Font.Style = {"fsBold"}
        labels.append(lbl_file)

        if len(file_paths) == 1:
            file_caption = os.path.basename(file_path)
        else:
            file_caption = f"{len(file_paths)} files selected (first: {os.path.basename(file_path)})"

        lbl_filename = vcl.TLabel(Form)
        lbl_filename.Parent = Form
        lbl_filename.Caption = file_caption
        lbl_filename.Left = 80
        lbl_filename.Top = 15
        lbl_filename.Width = 400
        lbl_filename.Font.Color = 0x666666
        labels.append(lbl_filename)

        # Separador visual
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 38
        sep1.Width = 490
        sep1.Height = 2
        sep1.Shape = "bsTopLine"

        # Option: has header
        chk_header = vcl.TCheckBox(Form)
        chk_header.Parent = Form
        chk_header.Caption = "File has header (first row with names)"
        chk_header.Left = 20
        chk_header.Top = 50
        chk_header.Width = 350
        chk_header.Checked = True

        # Field separator
        lbl_sep = vcl.TLabel(Form)
        lbl_sep.Parent = Form
        lbl_sep.Caption = "Field separator:"
        lbl_sep.Left = 20
        lbl_sep.Top = 80
        labels.append(lbl_sep)

        cb_separator = vcl.TComboBox(Form)
        cb_separator.Parent = Form
        cb_separator.Left = 130
        cb_separator.Top = 77
        cb_separator.Width = 120
        cb_separator.Style = "csDropDownList"
        cb_separator.Items.Add("auto (detect)")
        cb_separator.Items.Add(", (comma)")
        cb_separator.Items.Add("; (semicolon)")
        cb_separator.Items.Add("TAB (tabulator)")
        cb_separator.Items.Add("| (pipe)")
        cb_separator.ItemIndex = 0

        # Button to update columns after changing options
        btn_refresh = vcl.TButton(Form)
        btn_refresh.Parent = Form
        btn_refresh.Caption = "Detect columns"
        btn_refresh.Left = 270
        btn_refresh.Top = 75
        btn_refresh.Width = 120
        btn_refresh.Height = 25

        # Status label
        lbl_status = vcl.TLabel(Form)
        lbl_status.Parent = Form
        lbl_status.Caption = ""
        lbl_status.Left = 400
        lbl_status.Top = 80
        lbl_status.Font.Color = 0x008800
        labels.append(lbl_status)

        # === Skip initial rows ===
        lbl_skip = vcl.TLabel(Form)
        lbl_skip.Parent = Form
        lbl_skip.Caption = "Skip initial rows:"
        lbl_skip.Left = 20
        lbl_skip.Top = 115
        lbl_skip.Font.Style = {"fsBold"}
        labels.append(lbl_skip)

        edt_skip_rows = vcl.TEdit(Form)
        edt_skip_rows.Parent = Form
        edt_skip_rows.Left = 150
        edt_skip_rows.Top = 112
        edt_skip_rows.Width = 55
        edt_skip_rows.Text = "0"

        lbl_skip_hint = vcl.TLabel(Form)
        lbl_skip_hint.Parent = Form
        lbl_skip_hint.Caption = "(rows to skip before header/data)"
        lbl_skip_hint.Left = 212
        lbl_skip_hint.Top = 115
        lbl_skip_hint.Font.Color = 0x888888
        labels.append(lbl_skip_hint)

        # === Row range options ===
        lbl_row_range = vcl.TLabel(Form)
        lbl_row_range.Parent = Form
        lbl_row_range.Caption = "Row Range:"
        lbl_row_range.Left = 20
        lbl_row_range.Top = 147
        lbl_row_range.Font.Style = {"fsBold"}
        labels.append(lbl_row_range)

        lbl_start_row = vcl.TLabel(Form)
        lbl_start_row.Parent = Form
        lbl_start_row.Caption = "Start row:"
        lbl_start_row.Left = 120
        lbl_start_row.Top = 147
        labels.append(lbl_start_row)

        edt_start_row = vcl.TEdit(Form)
        edt_start_row.Parent = Form
        edt_start_row.Left = 185
        edt_start_row.Top = 144
        edt_start_row.Width = 60
        edt_start_row.Text = "1"

        lbl_row_limit = vcl.TLabel(Form)
        lbl_row_limit.Parent = Form
        lbl_row_limit.Caption = "Max rows:"
        lbl_row_limit.Left = 260
        lbl_row_limit.Top = 147
        labels.append(lbl_row_limit)

        edt_row_limit = vcl.TEdit(Form)
        edt_row_limit.Parent = Form
        edt_row_limit.Left = 325
        edt_row_limit.Top = 144
        edt_row_limit.Width = 60
        edt_row_limit.Text = ""

        lbl_row_hint = vcl.TLabel(Form)
        lbl_row_hint.Parent = Form
        lbl_row_hint.Caption = "(empty=all)"
        lbl_row_hint.Left = 390
        lbl_row_hint.Top = 147
        lbl_row_hint.Font.Color = 0x888888
        labels.append(lbl_row_hint)

        # === Decimation options ===
        lbl_decimate = vcl.TLabel(Form)
        lbl_decimate.Parent = Form
        lbl_decimate.Caption = "Decimation:"
        lbl_decimate.Left = 20
        lbl_decimate.Top = 182
        lbl_decimate.Font.Style = {"fsBold"}
        labels.append(lbl_decimate)

        chk_decimate = vcl.TCheckBox(Form)
        chk_decimate.Parent = Form
        chk_decimate.Caption = "Enable (1 point every N rows)"
        chk_decimate.Left = 110
        chk_decimate.Top = 182
        chk_decimate.Width = 230
        chk_decimate.Checked = False

        lbl_stride = vcl.TLabel(Form)
        lbl_stride.Parent = Form
        lbl_stride.Caption = "N:"
        lbl_stride.Left = 130
        lbl_stride.Top = 210
        labels.append(lbl_stride)

        edt_stride = vcl.TEdit(Form)
        edt_stride.Parent = Form
        edt_stride.Left = 150
        edt_stride.Top = 207
        edt_stride.Width = 55
        edt_stride.Text = "10"
        edt_stride.Enabled = False

        lbl_dec_method = vcl.TLabel(Form)
        lbl_dec_method.Parent = Form
        lbl_dec_method.Caption = "Method:"
        lbl_dec_method.Left = 215
        lbl_dec_method.Top = 210
        labels.append(lbl_dec_method)

        cb_decimate_method = vcl.TComboBox(Form)
        cb_decimate_method.Parent = Form
        cb_decimate_method.Left = 265
        cb_decimate_method.Top = 207
        cb_decimate_method.Width = 160
        cb_decimate_method.Style = "csDropDownList"
        cb_decimate_method.Items.Add("First point")
        cb_decimate_method.Items.Add("Average (mean)")
        cb_decimate_method.Items.Add("Median")
        cb_decimate_method.Items.Add("Minimum")
        cb_decimate_method.Items.Add("Maximum")
        cb_decimate_method.ItemIndex = 0
        cb_decimate_method.Enabled = False

        def on_decimate_toggle(_):
            enabled = chk_decimate.Checked
            edt_stride.Enabled = enabled
            cb_decimate_method.Enabled = enabled
        chk_decimate.OnClick = on_decimate_toggle

        # === NaN handling options ===
        lbl_nan = vcl.TLabel(Form)
        lbl_nan.Parent = Form
        lbl_nan.Caption = "NaN Handling:"
        lbl_nan.Left = 20
        lbl_nan.Top = 242
        lbl_nan.Font.Style = {"fsBold"}
        labels.append(lbl_nan)

        cb_nan_handling = vcl.TComboBox(Form)
        cb_nan_handling.Parent = Form
        cb_nan_handling.Left = 130
        cb_nan_handling.Top = 239
        cb_nan_handling.Width = 250
        cb_nan_handling.Style = "csDropDownList"
        cb_nan_handling.Items.Add("Delete rows with NaN values")
        cb_nan_handling.Items.Add("Fill with median of neighbors")
        cb_nan_handling.ItemIndex = 0

        # === X Column selector ===
        lbl_x_col = vcl.TLabel(Form)
        lbl_x_col.Parent = Form
        lbl_x_col.Caption = "X Column:"
        lbl_x_col.Left = 20
        lbl_x_col.Top = 277
        lbl_x_col.Font.Style = {"fsBold"}
        labels.append(lbl_x_col)

        cb_x_column = vcl.TComboBox(Form)
        cb_x_column.Parent = Form
        cb_x_column.Left = 130
        cb_x_column.Top = 274
        cb_x_column.Width = 250
        cb_x_column.Style = "csDropDownList"
        cb_x_column.Items.Add("None (X = 0, 1, 2...)")
        cb_x_column.ItemIndex = 0

        # === Fs (sampling frequency) — enabled when X = row index ===
        lbl_fs = vcl.TLabel(Form)
        lbl_fs.Parent = Form
        lbl_fs.Caption = "Fs [sps]:"
        lbl_fs.Left = 130
        lbl_fs.Top = 307
        labels.append(lbl_fs)

        edt_fs = vcl.TEdit(Form)
        edt_fs.Parent = Form
        edt_fs.Left = 195
        edt_fs.Top = 304
        edt_fs.Width = 80
        edt_fs.Text = "1.0"
        edt_fs.Enabled = True

        lbl_fs_hint = vcl.TLabel(Form)
        lbl_fs_hint.Parent = Form
        lbl_fs_hint.Caption = "(samples/sec, when X = row index)"
        lbl_fs_hint.Left = 282
        lbl_fs_hint.Top = 307
        lbl_fs_hint.Font.Color = 0x888888
        labels.append(lbl_fs_hint)

        # === Column selection panel ===
        lbl_columns = vcl.TLabel(Form)
        lbl_columns.Parent = Form
        lbl_columns.Caption = "Columns to Import:"
        lbl_columns.Left = 20
        lbl_columns.Top = 342
        lbl_columns.Font.Style = {"fsBold"}
        labels.append(lbl_columns)

        # Select All / Deselect All buttons
        btn_select_all = vcl.TButton(Form)
        btn_select_all.Parent = Form
        btn_select_all.Caption = "Select All"
        btn_select_all.Left = 160
        btn_select_all.Top = 338
        btn_select_all.Width = 80
        btn_select_all.Height = 22

        btn_deselect_all = vcl.TButton(Form)
        btn_deselect_all.Parent = Form
        btn_deselect_all.Caption = "Deselect All"
        btn_deselect_all.Left = 250
        btn_deselect_all.Top = 338
        btn_deselect_all.Width = 80
        btn_deselect_all.Height = 22

        # ScrollBox for column checkboxes
        scroll_box = vcl.TScrollBox(Form)
        scroll_box.Parent = Form
        scroll_box.Left = 20
        scroll_box.Top = 367
        scroll_box.Width = 470
        scroll_box.Height = 200
        scroll_box.BorderStyle = "bsSingle"
        scroll_box.Color = 0xFFFFFF

        def select_all_columns(Sender):
            for chk, _ in column_checkboxes:
                chk.Checked = True

        def deselect_all_columns(Sender):
            for chk, _ in column_checkboxes:
                chk.Checked = False

        btn_select_all.OnClick = select_all_columns
        btn_deselect_all.OnClick = deselect_all_columns

        def refresh_columns(Sender):
            """Detects and updates the list of available columns."""
            nonlocal column_checkboxes

            try:
                has_header = chk_header.Checked
                try:
                    skip_rows_val = max(0, int(edt_skip_rows.Text))
                except (ValueError, TypeError):
                    skip_rows_val = 0

                # Determinar separador
                sep_idx = cb_separator.ItemIndex
                if sep_idx == 0:
                    separator = detect_separator(file_path, has_header, skip_rows_val)
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
                headers, column_types, n_cols = detect_column_types(
                    file_path, has_header, separator, skip_rows_val)

                # Count total rows
                total_rows = count_data_rows(file_path, has_header, skip_rows_val)

                # Clear existing checkboxes
                for chk, _ in column_checkboxes:
                    chk.Free()
                column_checkboxes = []

                # Update X column combo
                cb_x_column.Items.Clear()
                cb_x_column.Items.Add("None (X = 0, 1, 2...)")

                usable_cols = 0
                checkbox_top = 5

                for i, (header, col_type) in enumerate(zip(headers, column_types)):
                    if col_type == 'ignore':
                        # Show ignored columns with different style
                        chk = vcl.TCheckBox(Form)
                        chk.Parent = scroll_box
                        chk.Left = 10
                        chk.Top = checkbox_top
                        chk.Width = 430
                        chk.Caption = f"{header} [text - ignored]"
                        chk.Checked = False
                        chk.Enabled = False
                        chk.Font.Color = 0x888888
                        column_checkboxes.append((chk, i))
                        checkbox_top += 22
                    else:
                        type_indicator = " [datetime→s]" if col_type == 'datetime' else " [numeric]"

                        # Add to X column combo
                        cb_x_column.Items.Add(f"{header}{type_indicator}")
                        usable_cols += 1

                        # Create checkbox for column selection
                        chk = vcl.TCheckBox(Form)
                        chk.Parent = scroll_box
                        chk.Left = 10
                        chk.Top = checkbox_top
                        chk.Width = 430
                        chk.Caption = f"{header}{type_indicator}"
                        chk.Checked = True  # Selected by default
                        column_checkboxes.append((chk, i))
                        checkbox_top += 22

                cb_x_column.ItemIndex = 0

                ignored = sum(1 for t in column_types if t == 'ignore')
                status_msg = f"{usable_cols} cols, {total_rows} rows"
                lbl_status.Caption = status_msg
                lbl_status.Font.Color = 0x008800

                # Save information for later use (in local variable)
                detected_info[0] = {
                    'headers': headers,
                    'column_types': column_types,
                    'separator': separator,
                    'n_cols': n_cols,
                    'total_rows': total_rows,
                    'skip_rows': skip_rows_val,
                }

            except Exception as e:
                lbl_status.Caption = f"Error: {str(e)[:20]}"
                lbl_status.Font.Color = 0x0000AA
                detected_info[0] = None

        btn_refresh.OnClick = refresh_columns

        def on_x_col_change(_):
            edt_fs.Enabled = (cb_x_column.ItemIndex == 0)
        cb_x_column.OnChange = on_x_col_change

        # Help panel
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 20
        help_panel.Top = 577
        help_panel.Width = 470
        help_panel.Height = 75
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0

        lbl_help_title = vcl.TLabel(Form)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Information:"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 5
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        help_text = (
            "• Select columns to import using checkboxes above\n"
            "• Decimation: keep 1 point per N rows (first/mean/median/min/max)\n"
            "• Row numbers are 1-based (row 1 = first data row after header)"
        )

        lbl_help = vcl.TLabel(Form)
        lbl_help.Parent = help_panel
        lbl_help.Caption = help_text
        lbl_help.Left = 10
        lbl_help.Top = 22
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)

        # Graph title
        sep_gt = vcl.TBevel(Form)
        sep_gt.Parent = Form
        sep_gt.Left = 10; sep_gt.Top = 662; sep_gt.Width = 490; sep_gt.Height = 2
        sep_gt.Shape = "bsTopLine"

        lbl_graph_title = vcl.TLabel(Form)
        lbl_graph_title.Parent = Form
        lbl_graph_title.Caption = "Graph title:"
        lbl_graph_title.Left = 20; lbl_graph_title.Top = 675
        lbl_graph_title.Font.Style = {"fsBold"}
        labels.append(lbl_graph_title)

        default_title = os.path.splitext(os.path.basename(file_path))[0].replace('_', ' ')
        edt_graph_title = vcl.TEdit(Form)
        edt_graph_title.Parent = Form
        edt_graph_title.Left = 110; edt_graph_title.Top = 672
        edt_graph_title.Width = 380; edt_graph_title.Text = default_title

        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Import"
        btn_ok.ModalResult = 1
        btn_ok.Default = True
        btn_ok.Left = 150
        btn_ok.Top = 704
        btn_ok.Width = 100
        btn_ok.Height = 30

        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        btn_cancel.Left = 270
        btn_cancel.Top = 704
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
                skip_rows = tag_data.get('skip_rows', 0)

                # Get row range options
                try:
                    start_row = int(edt_start_row.Text) - 1  # Convert to 0-based
                    if start_row < 0:
                        start_row = 0
                except ValueError:
                    start_row = 0

                row_limit_text = edt_row_limit.Text.strip()
                if row_limit_text:
                    try:
                        row_limit = int(row_limit_text)
                        if row_limit <= 0:
                            row_limit = None
                    except ValueError:
                        row_limit = None
                else:
                    row_limit = None

                # Get decimation options
                decimate_enabled = chk_decimate.Checked
                try:
                    stride = max(2, int(edt_stride.Text))
                except (ValueError, TypeError):
                    stride = 10
                decimate_method = cb_decimate_method.ItemIndex

                # Get NaN handling option
                nan_handling = cb_nan_handling.ItemIndex

                # Get selected columns
                selected_columns = []
                for chk, col_idx in column_checkboxes:
                    if chk.Checked and chk.Enabled:
                        selected_columns.append(col_idx)

                if not selected_columns:
                    raise ValueError("No columns selected for import")

                # Determine X column index
                x_selection = cb_x_column.ItemIndex
                if x_selection == 0:
                    x_col_index = -1
                else:
                    usable_idx = 0
                    x_col_index = -1
                    for i, col_type in enumerate(column_types):
                        if col_type != 'ignore':
                            usable_idx += 1
                            if usable_idx == x_selection:
                                x_col_index = i
                                break

                # Sampling frequency
                try:
                    fs = float(edt_fs.Text)
                    if fs <= 0:
                        fs = 1.0
                except (ValueError, TypeError):
                    fs = 1.0

                # ── Parse all files and merge same-named columns ──────────────
                # merged_series: {name: {'x': np.array, 'y': np.array}}
                merged_series = {}
                series_order = []  # preserve insertion order

                for fp in file_paths:
                    try:
                        if decimate_enabled:
                            s_names, x_vals, y_cols, _ = parse_csv_decimated(
                                fp, has_header, separator, x_col_index,
                                selected_columns=selected_columns,
                                nan_handling=nan_handling,
                                start_row=start_row,
                                row_limit=row_limit,
                                skip_rows=skip_rows,
                                stride=stride,
                                decimate_method=decimate_method,
                            )
                        else:
                            s_names, x_vals, y_cols, _ = parse_csv(
                                fp, has_header, separator, x_col_index,
                                selected_columns=selected_columns,
                                nan_handling=nan_handling,
                                start_row=start_row,
                                row_limit=row_limit,
                                skip_rows=skip_rows,
                            )
                    except Exception as e:
                        show_error(f"Error parsing {os.path.basename(fp)}:\n{str(e)}", "Import CSV")
                        continue

                    # Apply sampling frequency when using row index
                    if x_col_index == -1 and fs != 1.0:
                        x_vals = np.asarray(x_vals, dtype=float) / fs

                    for name, y_arr in zip(s_names, y_cols):
                        if name not in merged_series:
                            merged_series[name] = {'x': x_vals, 'y': y_arr}
                            series_order.append(name)
                        else:
                            prev = merged_series[name]
                            merged_series[name] = {
                                'x': np.concatenate([prev['x'], x_vals]),
                                'y': np.concatenate([prev['y'], y_arr]),
                            }

                if not merged_series:
                    raise ValueError("No data found in selected file(s)")

                # ── Create Graph series ───────────────────────────────────────
                series_created = 0
                total_points = 0

                for i, name in enumerate(series_order):
                    color = SERIES_COLORS[i % len(SERIES_COLORS)]
                    x_values = merged_series[name]['x']
                    y_values = merged_series[name]['y']

                    points = [
                        Point(float(x), float(y))
                        for x, y in zip(x_values, y_values)
                        if not (np.isnan(x) or np.isnan(y))
                    ]

                    if not points:
                        continue

                    new_series = Graph.TPointSeries()
                    new_series.PointType = Graph.ptCartesian
                    new_series.Points = points
                    new_series.LegendText = name
                    new_series.Size = 0
                    new_series.Style = 0
                    new_series.LineSize = 1
                    new_series.ShowLabels = False

                    color_val = safe_color(color)
                    new_series.FillColor = color_val
                    new_series.FrameColor = color_val
                    new_series.LineColor = color_val

                    Graph.FunctionList.append(new_series)
                    series_created += 1
                    total_points += len(points)

                Graph.Update()

                graph_title = edt_graph_title.Text.strip()
                if graph_title:
                    Graph.Axes.Title = graph_title
                    Graph.Update()

                nan_method = "deleted" if nan_handling == NAN_HANDLING_DELETE_ROW else "filled with median"
                files_str = (os.path.basename(file_paths[0]) if len(file_paths) == 1
                             else f"{len(file_paths)} files")

                decimate_info = ""
                if decimate_enabled:
                    method_names = ["first", "mean", "median", "min", "max"]
                    mname = method_names[decimate_method] if decimate_method < len(method_names) else "?"
                    decimate_info = f"\nDecimation: 1/{stride} ({mname})"

                show_info(
                    f"Import completed.\n\n"
                    f"File(s): {files_str}\n"
                    f"Series imported: {series_created}\n"
                    f"Total points: {total_points}\n"
                    f"NaN handling: {nan_method}"
                    f"{decimate_info}",
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
