# Plugin to import CSV files and convert them to point series
import os

from common import (
    show_error, show_info, safe_color, Point, Graph, vcl
)
from importing.csv_utils import (
    read_comment_header, try_parse_datetime, try_parse_number,
    detect_separator, detect_column_types, count_data_rows,
)

import numpy as np

PluginName = "Import CSV"
PluginVersion = "1.4"
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


def fill_nan_with_neighbor_median(arr, window=3):
    """Fills NaN values with the median of neighboring values."""
    result = arr.copy()
    nan_indices = np.where(np.isnan(result))[0]

    for idx in nan_indices:
        start = max(0, idx - window)
        end = min(len(result), idx + window + 1)
        neighbors = result[start:end]
        valid_neighbors = neighbors[~np.isnan(neighbors)]
        if len(valid_neighbors) > 0:
            result[idx] = np.median(valid_neighbors)

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

    cols_to_process = sorted(set(columns_to_use) | ({eff_x} if eff_x >= 0 else set()))

    dt_refs = {}
    col_bufs = {c: [] for c in cols_to_process}
    col_out = {c: [] for c in cols_to_process}
    x_idx_out = []

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
    """Parses the CSV file and returns (series_names, x_values, y_columns, n_rows)."""
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

    first_data = lines[start_idx].split(separator)
    n_cols = len(first_data)

    if headers is None:
        headers = [f"Series {i+1}" for i in range(n_cols)]

    _, column_types, _ = detect_column_types(file_path, has_header, separator, skip_rows)

    data_lines = lines[start_idx:]
    if start_row > 0:
        data_lines = data_lines[start_row:]
    if row_limit is not None and row_limit > 0:
        data_lines = data_lines[:row_limit]

    n_rows = len(data_lines)
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

    for col_idx in range(n_cols):
        if column_types[col_idx] == 'datetime':
            dt_values = column_data[col_idx]
            ref_time = next((v for v in dt_values if v is not None), None)
            if ref_time is not None:
                column_data[col_idx] = [
                    (v - ref_time).total_seconds() if v is not None else np.nan
                    for v in dt_values
                ]
            else:
                column_types[col_idx] = 'ignore'

    for col_idx in range(n_cols):
        if column_types[col_idx] != 'ignore':
            column_data[col_idx] = np.array(column_data[col_idx], dtype=float)

    if nan_handling == NAN_HANDLING_FILL_MEDIAN:
        for col_idx in range(n_cols):
            if column_types[col_idx] != 'ignore':
                column_data[col_idx] = fill_nan_with_neighbor_median(column_data[col_idx])

    if x_col_index >= 0 and x_col_index < n_cols and column_types[x_col_index] != 'ignore':
        x_values = column_data[x_col_index]
    else:
        x_values = np.arange(n_rows, dtype=float)
        x_col_index = -1

    if selected_columns is None:
        columns_to_use = [i for i in range(n_cols) if column_types[i] != 'ignore']
    else:
        columns_to_use = [i for i in selected_columns if i < n_cols and column_types[i] != 'ignore']

    y_columns = []
    series_names = []
    for col_idx in columns_to_use:
        if col_idx == x_col_index:
            continue
        y_columns.append(column_data[col_idx])
        series_names.append(headers[col_idx])

    if nan_handling == NAN_HANDLING_DELETE_ROW and y_columns:
        valid_mask = ~np.isnan(x_values)
        for y_col in y_columns:
            valid_mask &= ~np.isnan(y_col)
        x_values = x_values[valid_mask]
        y_columns = [y_col[valid_mask] for y_col in y_columns]
        n_rows = len(x_values)

    return series_names, x_values, y_columns, n_rows


def import_csv(Action):
    """Imports one or more CSV files and creates point series."""

    open_dialog = vcl.TOpenDialog(None)
    open_dialog.Title = "Select CSV file(s)"
    open_dialog.Filter = "Archivos CSV (*.csv)|*.csv|Archivos de texto (*.txt)|*.txt|Todos los archivos (*.*)|*.*"
    open_dialog.FilterIndex = 1
    open_dialog.Options = "ofFileMustExist,ofHideReadOnly,ofAllowMultiSelect"

    if not open_dialog.Execute():
        return

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

    file_path = file_paths[0]
    _n_comments, _rate_hz, _start_utc = read_comment_header(file_path)

    detected_info = [None]
    column_checkboxes = []

    Form = vcl.TForm(None)
    try:
        Form.Caption = "CSV Import Configuration"
        Form.Width = 520
        Form.Height = 815
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"

        labels = []

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

        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 38
        sep1.Width = 490
        sep1.Height = 2
        sep1.Shape = "bsTopLine"

        chk_header = vcl.TCheckBox(Form)
        chk_header.Parent = Form
        chk_header.Caption = "File has header (first row with names)"
        chk_header.Left = 20
        chk_header.Top = 50
        chk_header.Width = 350
        chk_header.Checked = True

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

        btn_refresh = vcl.TButton(Form)
        btn_refresh.Parent = Form
        btn_refresh.Caption = "Detect columns"
        btn_refresh.Left = 270
        btn_refresh.Top = 75
        btn_refresh.Width = 120
        btn_refresh.Height = 25

        lbl_status = vcl.TLabel(Form)
        lbl_status.Parent = Form
        lbl_status.Caption = ""
        lbl_status.Left = 400
        lbl_status.Top = 80
        lbl_status.Font.Color = 0x008800
        labels.append(lbl_status)

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
        edt_skip_rows.Text = str(_n_comments)

        lbl_skip_hint = vcl.TLabel(Form)
        lbl_skip_hint.Parent = Form
        lbl_skip_hint.Caption = "(rows to skip before header/data)"
        lbl_skip_hint.Left = 212
        lbl_skip_hint.Top = 115
        lbl_skip_hint.Font.Color = 0x888888
        labels.append(lbl_skip_hint)

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
        edt_fs.Text = str(_rate_hz) if _rate_hz is not None else "1.0"
        edt_fs.Enabled = True

        lbl_fs_hint = vcl.TLabel(Form)
        lbl_fs_hint.Parent = Form
        lbl_fs_hint.Caption = "(samples/sec, when X = row index)"
        lbl_fs_hint.Left = 282
        lbl_fs_hint.Top = 307
        lbl_fs_hint.Font.Color = 0x888888
        labels.append(lbl_fs_hint)

        _multi = len(file_paths) > 1

        chk_stack = vcl.TCheckBox(Form)
        chk_stack.Parent = Form
        chk_stack.Caption = "Stack datasets on X axis"
        chk_stack.Left = 130
        chk_stack.Top = 333
        chk_stack.Width = 185
        chk_stack.Checked = _multi
        chk_stack.Enabled = _multi

        lbl_sort = vcl.TLabel(Form)
        lbl_sort.Parent = Form
        lbl_sort.Caption = "Sort by:"
        lbl_sort.Left = 322
        lbl_sort.Top = 336
        lbl_sort.Enabled = _multi
        labels.append(lbl_sort)

        cb_sort_order = vcl.TComboBox(Form)
        cb_sort_order.Parent = Form
        cb_sort_order.Left = 375
        cb_sort_order.Top = 333
        cb_sort_order.Width = 115
        cb_sort_order.Style = "csDropDownList"
        cb_sort_order.Items.Add("Name")
        cb_sort_order.Items.Add("Creation date")
        cb_sort_order.ItemIndex = 0
        cb_sort_order.Enabled = _multi

        lbl_columns = vcl.TLabel(Form)
        lbl_columns.Parent = Form
        lbl_columns.Caption = "Columns to Import:"
        lbl_columns.Left = 20
        lbl_columns.Top = 377
        lbl_columns.Font.Style = {"fsBold"}
        labels.append(lbl_columns)

        btn_select_all = vcl.TButton(Form)
        btn_select_all.Parent = Form
        btn_select_all.Caption = "Select All"
        btn_select_all.Left = 160
        btn_select_all.Top = 373
        btn_select_all.Width = 80
        btn_select_all.Height = 22

        btn_deselect_all = vcl.TButton(Form)
        btn_deselect_all.Parent = Form
        btn_deselect_all.Caption = "Deselect All"
        btn_deselect_all.Left = 250
        btn_deselect_all.Top = 373
        btn_deselect_all.Width = 80
        btn_deselect_all.Height = 22

        scroll_box = vcl.TScrollBox(Form)
        scroll_box.Parent = Form
        scroll_box.Left = 20
        scroll_box.Top = 402
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
            nonlocal column_checkboxes
            try:
                has_header = chk_header.Checked
                try:
                    skip_rows_val = max(0, int(edt_skip_rows.Text))
                except (ValueError, TypeError):
                    skip_rows_val = 0

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

                headers, column_types, n_cols = detect_column_types(
                    file_path, has_header, separator, skip_rows_val)

                total_rows = count_data_rows(file_path, has_header, skip_rows_val)

                for chk, _ in column_checkboxes:
                    chk.Free()
                column_checkboxes = []

                cb_x_column.Items.Clear()
                cb_x_column.Items.Add("None (X = 0, 1, 2...)")

                usable_cols = 0
                checkbox_top = 5

                for i, (header, col_type) in enumerate(zip(headers, column_types)):
                    if col_type == 'ignore':
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
                        cb_x_column.Items.Add(f"{header}{type_indicator}")
                        usable_cols += 1
                        chk = vcl.TCheckBox(Form)
                        chk.Parent = scroll_box
                        chk.Left = 10
                        chk.Top = checkbox_top
                        chk.Width = 430
                        chk.Caption = f"{header}{type_indicator}"
                        chk.Checked = True
                        column_checkboxes.append((chk, i))
                        checkbox_top += 22

                cb_x_column.ItemIndex = 0

                lbl_status.Caption = f"{usable_cols} cols, {total_rows} rows"
                lbl_status.Font.Color = 0x008800

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
            is_row_index = (cb_x_column.ItemIndex == 0)
            edt_fs.Enabled = is_row_index
            chk_stack.Enabled = is_row_index and len(file_paths) > 1
            lbl_sort.Enabled = is_row_index and len(file_paths) > 1
            cb_sort_order.Enabled = is_row_index and len(file_paths) > 1
        cb_x_column.OnChange = on_x_col_change

        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 20
        help_panel.Top = 612
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

        lbl_help = vcl.TLabel(Form)
        lbl_help.Parent = help_panel
        lbl_help.Caption = (
            "• Select columns to import using checkboxes above\n"
            "• Decimation: keep 1 point per N rows (first/mean/median/min/max)\n"
            "• Row numbers are 1-based (row 1 = first data row after header)"
        )
        lbl_help.Left = 10
        lbl_help.Top = 22
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)

        sep_gt = vcl.TBevel(Form)
        sep_gt.Parent = Form
        sep_gt.Left = 10; sep_gt.Top = 697; sep_gt.Width = 490; sep_gt.Height = 2
        sep_gt.Shape = "bsTopLine"

        lbl_graph_title = vcl.TLabel(Form)
        lbl_graph_title.Parent = Form
        lbl_graph_title.Caption = "Graph title:"
        lbl_graph_title.Left = 20; lbl_graph_title.Top = 710
        lbl_graph_title.Font.Style = {"fsBold"}
        labels.append(lbl_graph_title)

        default_title = os.path.splitext(os.path.basename(file_path))[0].replace('_', ' ')
        if _start_utc:
            default_title += f" [{_start_utc}]"
        edt_graph_title = vcl.TEdit(Form)
        edt_graph_title.Parent = Form
        edt_graph_title.Left = 110; edt_graph_title.Top = 707
        edt_graph_title.Width = 380; edt_graph_title.Text = default_title

        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Import"
        btn_ok.ModalResult = 1
        btn_ok.Default = True
        btn_ok.Left = 150
        btn_ok.Top = 739
        btn_ok.Width = 100
        btn_ok.Height = 30

        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        btn_cancel.Left = 270
        btn_cancel.Top = 739
        btn_cancel.Width = 100
        btn_cancel.Height = 30

        refresh_columns(None)

        if Form.ShowModal() == 1:
            try:
                has_header = chk_header.Checked

                tag_data = detected_info[0]
                if not tag_data:
                    raise ValueError("Press 'Detect columns' first")

                separator = tag_data['separator']
                headers = tag_data['headers']
                column_types = tag_data['column_types']
                skip_rows = tag_data.get('skip_rows', 0)

                try:
                    start_row = int(edt_start_row.Text) - 1
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

                decimate_enabled = chk_decimate.Checked
                try:
                    stride = max(2, int(edt_stride.Text))
                except (ValueError, TypeError):
                    stride = 10
                decimate_method = cb_decimate_method.ItemIndex

                nan_handling = cb_nan_handling.ItemIndex

                selected_columns = []
                for chk, col_idx in column_checkboxes:
                    if chk.Checked and chk.Enabled:
                        selected_columns.append(col_idx)

                if not selected_columns:
                    raise ValueError("No columns selected for import")

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

                try:
                    fs = float(edt_fs.Text)
                    if fs <= 0:
                        fs = 1.0
                except (ValueError, TypeError):
                    fs = 1.0

                stack_enabled = (
                    chk_stack.Checked
                    and x_col_index == -1
                    and len(file_paths) > 1
                )
                if stack_enabled:
                    sort_by_date = (cb_sort_order.ItemIndex == 1)
                    if sort_by_date:
                        files_to_process = sorted(
                            file_paths, key=lambda f: os.path.getmtime(f))
                    else:
                        files_to_process = sorted(
                            file_paths, key=lambda f: os.path.basename(f).lower())
                else:
                    files_to_process = file_paths

                merged_series = {}
                series_order = []
                x_stack_offset = 0.0

                for fp in files_to_process:
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

                    if stack_enabled:
                        raw_count = count_data_rows(fp, has_header, skip_rows)
                        imported_count = max(0, raw_count - start_row)
                        if row_limit is not None:
                            imported_count = min(imported_count, row_limit)
                        x_vals = np.asarray(x_vals, dtype=float) + x_stack_offset
                        x_stack_offset += imported_count

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

                stack_info = ""
                if stack_enabled:
                    sort_label = "creation date" if cb_sort_order.ItemIndex == 1 else "name"
                    stack_info = f"\nStacking: sequential X (sorted by {sort_label})"

                show_info(
                    f"Import completed.\n\n"
                    f"File(s): {files_str}\n"
                    f"Series imported: {series_created}\n"
                    f"Total points: {total_points}\n"
                    f"NaN handling: {nan_method}"
                    f"{decimate_info}"
                    f"{stack_info}",
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

Graph.AddActionToMainMenu(ImportCSVAction, TopMenu="Plugins", SubMenus=["Graphîa", "Import/Export"])
