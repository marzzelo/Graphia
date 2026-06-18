# Plugin: CSV Envelope Plotter
# Streams CSV file row-by-row computing max/min/mean envelope curves per period.
# Memory complexity: O(period_size x n_cols) regardless of file size.
import os
import math
from datetime import datetime

from common import show_error, show_info, safe_color, SERIES_COLORS, Point, Graph, vcl

PluginName = "CSV Envelope"
PluginVersion = "1.0"
PluginDescription = (
    "Plots max/min/mean envelope curves from CSV signal columns "
    "using streaming (low memory)."
)

# ─── Detection utilities (copied from CSVImporter) ───────────────────────────

DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S.%f",
    "%Y/%m/%d %H:%M:%S",
    "%d-%m-%Y %H:%M:%S.%f",
    "%d-%m-%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S.%f",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%H:%M:%S.%f",
    "%H:%M:%S",
]


def _try_parse_datetime(value):
    value = value.strip().strip('"').strip("'")
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _try_parse_number(value, separator):
    value = value.strip().strip('"').strip("'")
    try:
        return float(value)
    except ValueError:
        pass
    if separator != ',':
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            pass
    return None


def _detect_separator(file_path, has_header, skip_rows=0):
    separators = [',', ';', '\t', '|']
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        all_lines = []
        for i, line in enumerate(f):
            if i >= 6 + skip_rows:
                break
            all_lines.append(line.rstrip('\n\r'))
    if not all_lines:
        return ','
    all_lines = all_lines[skip_rows:]
    if not all_lines:
        return ','
    # Skip header line — it may have a different column count than data rows
    lines = all_lines[1:] if has_header and len(all_lines) > 1 else all_lines
    best_sep, best_count = ',', 0
    for sep in separators:
        counts = [line.count(sep) for line in lines if line]
        if counts and min(counts) > 0 and max(counts) == min(counts):
            if counts[0] > best_count:
                best_count = counts[0]
                best_sep = sep
    return best_sep


def _detect_column_types(file_path, has_header, separator, skip_rows=0):
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
        headers = [h.strip().strip('"').strip("'")
                   for h in lines[0].split(separator)]
        start_idx = 1
    if start_idx >= len(lines):
        raise ValueError("No data after header")
    first_data = lines[start_idx].split(separator)
    n_cols = len(first_data)
    if headers is None:
        headers = [str(i) for i in range(n_cols)]
    sample = lines[start_idx:start_idx + min(10, len(lines) - start_idx)]
    column_types = []
    for col_idx in range(n_cols):
        num_c = dt_c = empty_c = 0
        for line in sample:
            parts = line.split(separator)
            if col_idx >= len(parts):
                continue
            v = parts[col_idx].strip().strip('"').strip("'")
            if not v:
                empty_c += 1
                continue
            if _try_parse_number(v, separator) is not None:
                num_c += 1
            elif _try_parse_datetime(v) is not None:
                dt_c += 1
        total = len(sample) - empty_c
        if total > 0:
            if num_c >= total * 0.8:
                column_types.append('numeric')
            elif dt_c >= total * 0.8:
                column_types.append('datetime')
            else:
                column_types.append('ignore')
        else:
            column_types.append('ignore')
    return headers, column_types, n_cols


# ─── X-range quick scan ───────────────────────────────────────────────────────

def _quick_scan_xrange(file_path, has_header, separator, x_col_idx, x_col_type, skip_rows=0):
    """
    Reads first data row + last ~4 KB to estimate x_first, x_last, approx_rows.
    Returns (x_first_secs, x_last_secs, approx_total_rows, first_datetime_ref).
    """
    first_datetime_ref = None

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        for _ in range(skip_rows):
            f.readline()
        if has_header:
            f.readline()
        pos_before = f.tell()
        first_line = f.readline()
        pos_after = f.tell()
        bytes_first = max(1, pos_after - pos_before)

        f.seek(0, 2)
        file_size = f.tell()
        approx_total_rows = max(1, int(file_size / bytes_first * 0.9))

        # Last ~4 KB
        seek_pos = max(pos_after, file_size - 4096)
        f.seek(seek_pos)
        tail = f.read()

    def parse_x_from_line(line):
        parts = line.split(separator)
        if x_col_idx >= len(parts):
            return None
        raw = parts[x_col_idx].strip().strip('"').strip("'")
        if x_col_type == 'datetime':
            return _try_parse_datetime(raw)
        return _try_parse_number(raw, separator)

    x_first_raw = parse_x_from_line(first_line)
    if x_first_raw is None:
        return 0.0, 100.0, approx_total_rows, None

    # Find last parseable line
    tail_lines = [l for l in tail.splitlines() if l.strip()]
    x_last_raw = None
    for line in reversed(tail_lines):
        v = parse_x_from_line(line)
        if v is not None:
            x_last_raw = v
            break

    if x_col_type == 'datetime':
        if isinstance(x_first_raw, datetime):
            first_datetime_ref = x_first_raw
            x_first_secs = 0.0
            if isinstance(x_last_raw, datetime):
                x_last_secs = (x_last_raw - first_datetime_ref).total_seconds()
            else:
                x_last_secs = float(approx_total_rows)
        else:
            return 0.0, float(approx_total_rows), approx_total_rows, None
    else:
        x_first_secs = float(x_first_raw) if x_first_raw is not None else 0.0
        x_last_secs = float(x_last_raw) if x_last_raw is not None else x_first_secs + approx_total_rows

    return x_first_secs, x_last_secs, approx_total_rows, first_datetime_ref


# ─── Streaming helpers ────────────────────────────────────────────────────────

def _parse_x_val(parts, x_col_idx, x_col_type, separator, ref):
    """Returns float x-value or None."""
    if x_col_idx >= len(parts):
        return None
    raw = parts[x_col_idx].strip().strip('"').strip("'")
    if x_col_type == 'datetime':
        dt = _try_parse_datetime(raw)
        if dt is None:
            return None
        if ref[0] is None:
            ref[0] = dt
        return (dt - ref[0]).total_seconds()
    return _try_parse_number(raw, separator)


def _parse_y_val(parts, col_idx, separator):
    """Returns float or None (NaN/missing → None, silent skip)."""
    if col_idx >= len(parts):
        return None
    raw = parts[col_idx].strip().strip('"').strip("'")
    if not raw or raw.lower() in ('nan', 'null', 'none', 'n/a', '#n/a'):
        return None
    return _try_parse_number(raw, separator)


def _smooth(values, window):
    """Simple centred moving average. Returns same-length list."""
    if window <= 1 or len(values) < 2:
        return list(values)
    result = []
    n = len(values)
    hw = window // 2
    for i in range(n):
        lo = max(0, i - hw)
        hi = min(n, i + hw + 1)
        chunk = [v for v in values[lo:hi] if v is not None]
        result.append(sum(chunk) / len(chunk) if chunk else None)
    return result


# ─── Core streaming algorithm ─────────────────────────────────────────────────

def compute_envelope(file_path, has_header, separator,
                     x_col_idx, y_col_indices, x_col_type,
                     period, use_time_based,
                     overlap_frac,
                     pct_low, pct_high,
                     x_pos,
                     include_mean,
                     smooth_window,
                     first_datetime_ref=None,
                     fs=1.0,
                     skip_rows=0):
    """
    One-pass streaming envelope computation.

    win_rows: list of (x, [y0_or_None, y1_or_None, ...]) — one entry per row.
    Memory: O(period_size × n_cols) at any moment.

    Parameters
    ----------
    period        : float — window size (seconds or rows)
    use_time_based: bool
    overlap_frac  : 0.0–0.9 — fraction of period retained after each flush
    pct_low/high  : 0–100 — percentile for lower/upper envelope (0/100 = min/max)
    x_pos         : 'start'|'center'|'end'
    include_mean  : bool
    smooth_window : int — moving-average window over result points (1 = off)
    """
    n_y = len(y_col_indices)
    x_pts    = []
    col_upper = [[] for _ in range(n_y)]
    col_lower = [[] for _ in range(n_y)]
    col_mean  = [[] for _ in range(n_y)] if include_mean else None

    ref = [first_datetime_ref]   # mutable container for datetime ref
    use_row_index = (x_col_idx is None or x_col_idx < 0)

    # step = how far the window advances after each flush
    step_frac   = max(0.0, min(0.9, overlap_frac))
    period_int  = max(1, int(period))      # used for sample-based only
    step_rows   = max(1, int(period_int * (1.0 - step_frac)))
    step_time   = max(1e-12, period * (1.0 - step_frac))

    # win_rows stores complete rows as (x, [y0_or_None, ...])
    win_rows       = []
    window_start_x = None
    row_count      = 0

    def _flush_window(rows):
        if not rows:
            return
        xs = [r[0] for r in rows]
        if x_pos == 'start':
            xv = xs[0]
        elif x_pos == 'end':
            xv = xs[-1]
        else:
            xv = (xs[0] + xs[-1]) / 2.0
        x_pts.append(xv)
        for i in range(n_y):
            yv = [r[1][i] for r in rows if r[1][i] is not None]
            if yv:
                sorted_y = sorted(yv)
                n = len(sorted_y)
                lo_idx = max(0, int(math.floor(pct_low  / 100.0 * (n - 1))))
                hi_idx = min(n - 1, int(math.floor(pct_high / 100.0 * (n - 1))))
                col_lower[i].append(sorted_y[lo_idx])
                col_upper[i].append(sorted_y[hi_idx])
                if include_mean:
                    col_mean[i].append(sum(yv) / len(yv))
            else:
                col_lower[i].append(None)
                col_upper[i].append(None)
                if include_mean:
                    col_mean[i].append(None)

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        for _ in range(skip_rows):
            f.readline()
        if has_header:
            f.readline()

        for raw_line in f:
            line = raw_line.rstrip('\n\r')
            if not line.strip():
                continue
            parts = line.split(separator)

            # Determine x for this row
            if use_row_index:
                x = float(row_count) / fs
            else:
                x = _parse_x_val(parts, x_col_idx, x_col_type, separator, ref)
                if x is None:
                    continue

            row_count += 1

            if window_start_x is None:
                window_start_x = x

            # Check if window is full
            if use_time_based:
                exceeded = x >= window_start_x + period
            else:
                exceeded = len(win_rows) >= period_int

            while exceeded:
                _flush_window(win_rows)

                if use_time_based:
                    window_start_x += step_time
                    # Keep only rows within the new window
                    win_rows = [r for r in win_rows if r[0] >= window_start_x]
                    exceeded = x >= window_start_x + period
                else:
                    win_rows = win_rows[step_rows:]
                    window_start_x = win_rows[0][0] if win_rows else x
                    exceeded = len(win_rows) >= period_int

            # Parse Y values (None where missing/NaN)
            y_vals = [_parse_y_val(parts, col_idx, separator)
                      for col_idx in y_col_indices]

            win_rows.append((x, y_vals))

    # Flush last (possibly partial) window
    if win_rows:
        _flush_window(win_rows)

    # Post-processing: smoothing over envelope points
    if smooth_window > 1:
        for i in range(n_y):
            col_upper[i] = _smooth(col_upper[i], smooth_window)
            col_lower[i] = _smooth(col_lower[i], smooth_window)
            if include_mean:
                col_mean[i] = _smooth(col_mean[i], smooth_window)

    return x_pts, col_upper, col_lower, col_mean


# ─── Main action ──────────────────────────────────────────────────────────────

def plot_envelope(Action):
    """Entry point: file dialog → config dialog → compute → add series."""

    open_dialog = vcl.TOpenDialog(None)
    open_dialog.Title = "Select CSV file for Envelope"
    open_dialog.Filter = (
        "CSV files (*.csv)|*.csv|Text files (*.txt)|*.txt|All files (*.*)|*.*"
    )
    open_dialog.FilterIndex = 1
    open_dialog.Options = "ofFileMustExist,ofHideReadOnly"

    if not open_dialog.Execute():
        return

    file_path = open_dialog.FileName
    if not os.path.exists(file_path):
        show_error(f"File not found:\n{file_path}", "CSV Envelope")
        return

    detected_info = [None]
    column_checkboxes = []   # list of (TCheckBox, col_index, col_name)
    x_col_map = [None]       # [0] = list of (col_index, col_type) matching cb_x_column items

    # ── Build form ───────────────────────────────────────────────────────────
    Form = vcl.TForm(None)
    try:
        Form.Caption = "CSV Envelope Configuration"
        Form.Width = 530
        Form.Height = 740
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"

        y_top = 10

        # Title panel
        title_panel = vcl.TPanel(Form)
        title_panel.Parent = Form
        title_panel.Left = 10
        title_panel.Top = y_top
        title_panel.Width = 500
        title_panel.Height = 52
        title_panel.BevelOuter = "bvLowered"
        title_panel.Color = 0xFFF8F0

        lbl_title = vcl.TLabel(Form)
        lbl_title.Parent = title_panel
        lbl_title.Caption = "CSV Envelope Plotter"
        lbl_title.Left = 10
        lbl_title.Top = 5
        lbl_title.Font.Style = {"fsBold"}
        lbl_title.Font.Color = 0x804000
        lbl_title.Font.Size = 10

        lbl_file_info = vcl.TLabel(Form)
        lbl_file_info.Parent = title_panel
        lbl_file_info.Caption = os.path.basename(file_path)
        lbl_file_info.Left = 10
        lbl_file_info.Top = 28
        lbl_file_info.Font.Color = 0x804000

        y_top += 62

        # ── Graph title ─────────────────────────────────────────────────────
        sep_title = vcl.TBevel(Form)
        sep_title.Parent = Form
        sep_title.Left = 10; sep_title.Top = y_top; sep_title.Width = 500; sep_title.Height = 2
        sep_title.Shape = "bsTopLine"
        y_top += 8

        lbl_graph_title = vcl.TLabel(Form)
        lbl_graph_title.Parent = Form
        lbl_graph_title.Caption = "Graph title:"
        lbl_graph_title.Left = 15; lbl_graph_title.Top = y_top + 3
        lbl_graph_title.Font.Style = {"fsBold"}

        default_title = os.path.splitext(os.path.basename(file_path))[0].replace('_', ' ')
        edt_graph_title = vcl.TEdit(Form)
        edt_graph_title.Parent = Form
        edt_graph_title.Left = 110; edt_graph_title.Top = y_top
        edt_graph_title.Width = 400; edt_graph_title.Text = default_title

        y_top += 32

        # ── Separator & header ──────────────────────────────────────────────
        sep0 = vcl.TBevel(Form)
        sep0.Parent = Form
        sep0.Left = 10; sep0.Top = y_top; sep0.Width = 500; sep0.Height = 2
        sep0.Shape = "bsTopLine"
        y_top += 8

        chk_header = vcl.TCheckBox(Form)
        chk_header.Parent = Form
        chk_header.Caption = "File has header row"
        chk_header.Left = 15; chk_header.Top = y_top
        chk_header.Width = 180; chk_header.Checked = True

        lbl_sep = vcl.TLabel(Form)
        lbl_sep.Parent = Form
        lbl_sep.Caption = "Separator:"
        lbl_sep.Left = 210; lbl_sep.Top = y_top + 2

        cb_separator = vcl.TComboBox(Form)
        cb_separator.Parent = Form
        cb_separator.Left = 275; cb_separator.Top = y_top - 1
        cb_separator.Width = 115; cb_separator.Style = "csDropDownList"
        for item in ["auto", ", (comma)", "; (semicolon)", "TAB", "| (pipe)"]:
            cb_separator.Items.Add(item)
        cb_separator.ItemIndex = 0

        btn_detect = vcl.TButton(Form)
        btn_detect.Parent = Form
        btn_detect.Caption = "Detect columns"
        btn_detect.Left = 400; btn_detect.Top = y_top - 2
        btn_detect.Width = 110; btn_detect.Height = 24

        lbl_status = vcl.TLabel(Form)
        lbl_status.Parent = Form
        lbl_status.Caption = ""
        lbl_status.Left = 15; lbl_status.Top = y_top + 24
        lbl_status.Font.Color = 0x008800

        y_top += 48

        # ── Skip rows ────────────────────────────────────────────────────────
        lbl_skip = vcl.TLabel(Form)
        lbl_skip.Parent = Form
        lbl_skip.Caption = "Skip initial rows:"
        lbl_skip.Left = 15; lbl_skip.Top = y_top + 3

        edt_skip_rows = vcl.TEdit(Form)
        edt_skip_rows.Parent = Form
        edt_skip_rows.Left = 130; edt_skip_rows.Top = y_top
        edt_skip_rows.Width = 55; edt_skip_rows.Text = "0"

        lbl_skip_hint = vcl.TLabel(Form)
        lbl_skip_hint.Parent = Form
        lbl_skip_hint.Caption = "(rows to skip before header/data)"
        lbl_skip_hint.Left = 192; lbl_skip_hint.Top = y_top + 3
        lbl_skip_hint.Font.Color = 0x888888

        y_top += 30

        # ── X column ────────────────────────────────────────────────────────
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10; sep1.Top = y_top; sep1.Width = 500; sep1.Height = 2
        sep1.Shape = "bsTopLine"
        y_top += 8

        lbl_x = vcl.TLabel(Form)
        lbl_x.Parent = Form
        lbl_x.Caption = "X Column (time axis):"
        lbl_x.Left = 15; lbl_x.Top = y_top + 3
        lbl_x.Font.Style = {"fsBold"}

        cb_x_column = vcl.TComboBox(Form)
        cb_x_column.Parent = Form
        cb_x_column.Left = 180; cb_x_column.Top = y_top
        cb_x_column.Width = 310; cb_x_column.Style = "csDropDownList"
        cb_x_column.Items.Add("(none — use row index)")
        cb_x_column.ItemIndex = 0

        y_top += 32

        # ── Fs (sampling frequency) ──────────────────────────────────────────
        lbl_fs = vcl.TLabel(Form)
        lbl_fs.Parent = Form
        lbl_fs.Caption = "Fs [sps]:"
        lbl_fs.Left = 15; lbl_fs.Top = y_top + 3
        lbl_fs.Font.Style = {"fsBold"}

        edt_fs = vcl.TEdit(Form)
        edt_fs.Parent = Form
        edt_fs.Left = 180; edt_fs.Top = y_top
        edt_fs.Width = 100; edt_fs.Text = "1.0"
        edt_fs.Enabled = True

        lbl_fs_hint = vcl.TLabel(Form)
        lbl_fs_hint.Parent = Form
        lbl_fs_hint.Caption = "(samples/sec, when X = row index)"
        lbl_fs_hint.Left = 285; lbl_fs_hint.Top = y_top + 3
        lbl_fs_hint.Font.Color = 0x888888

        y_top += 32

        # ── Y columns ───────────────────────────────────────────────────────
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10; sep2.Top = y_top; sep2.Width = 500; sep2.Height = 2
        sep2.Shape = "bsTopLine"
        y_top += 8

        lbl_y = vcl.TLabel(Form)
        lbl_y.Parent = Form
        lbl_y.Caption = "Y Columns to plot:"
        lbl_y.Left = 15; lbl_y.Top = y_top
        lbl_y.Font.Style = {"fsBold"}

        btn_all = vcl.TButton(Form)
        btn_all.Parent = Form
        btn_all.Caption = "All"
        btn_all.Left = 180; btn_all.Top = y_top - 3
        btn_all.Width = 50; btn_all.Height = 22

        btn_none = vcl.TButton(Form)
        btn_none.Parent = Form
        btn_none.Caption = "None"
        btn_none.Left = 235; btn_none.Top = y_top - 3
        btn_none.Width = 50; btn_none.Height = 22

        y_top += 26

        scroll_box = vcl.TScrollBox(Form)
        scroll_box.Parent = Form
        scroll_box.Left = 15; scroll_box.Top = y_top
        scroll_box.Width = 495; scroll_box.Height = 110
        scroll_box.BorderStyle = "bsSingle"
        scroll_box.Color = 0xFFFFFF

        y_top += 118

        def select_all(Sender):
            for chk, _, __ in column_checkboxes:
                if chk.Enabled:
                    chk.Checked = True

        def select_none(Sender):
            for chk, _, __ in column_checkboxes:
                chk.Checked = False

        btn_all.OnClick  = select_all
        btn_none.OnClick = select_none

        # ── Period ──────────────────────────────────────────────────────────
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10; sep3.Top = y_top; sep3.Width = 500; sep3.Height = 2
        sep3.Shape = "bsTopLine"
        y_top += 8

        lbl_period = vcl.TLabel(Form)
        lbl_period.Parent = Form
        lbl_period.Caption = "Envelope period:"
        lbl_period.Left = 15; lbl_period.Top = y_top
        lbl_period.Font.Style = {"fsBold"}
        y_top += 22

        rb_time = vcl.TRadioButton(Form)
        rb_time.Parent = Form
        rb_time.Caption = "Time-based (sec):"
        rb_time.Left = 25; rb_time.Top = y_top
        rb_time.Width = 155; rb_time.Checked = True

        edt_time = vcl.TEdit(Form)
        edt_time.Parent = Form
        edt_time.Left = 185; edt_time.Top = y_top - 2
        edt_time.Width = 80; edt_time.Text = "60"

        lbl_time_hint = vcl.TLabel(Form)
        lbl_time_hint.Parent = Form
        lbl_time_hint.Caption = "(seconds)"
        lbl_time_hint.Left = 272; lbl_time_hint.Top = y_top + 2
        lbl_time_hint.Font.Color = 0x888888

        y_top += 28

        rb_sample = vcl.TRadioButton(Form)
        rb_sample.Parent = Form
        rb_sample.Caption = "Sample-based (rows):"
        rb_sample.Left = 25; rb_sample.Top = y_top
        rb_sample.Width = 160; rb_sample.Checked = False

        edt_sample = vcl.TEdit(Form)
        edt_sample.Parent = Form
        edt_sample.Left = 185; edt_sample.Top = y_top - 2
        edt_sample.Width = 80; edt_sample.Text = "1000"
        edt_sample.Enabled = False

        y_top += 28

        rb_points = vcl.TRadioButton(Form)
        rb_points.Parent = Form
        rb_points.Caption = "Total points-based:"
        rb_points.Left = 25; rb_points.Top = y_top
        rb_points.Width = 160; rb_points.Checked = False

        edt_points = vcl.TEdit(Form)
        edt_points.Parent = Form
        edt_points.Left = 185; edt_points.Top = y_top - 2
        edt_points.Width = 80; edt_points.Text = "1000"
        edt_points.Enabled = False

        lbl_points_hint = vcl.TLabel(Form)
        lbl_points_hint.Parent = Form
        lbl_points_hint.Caption = "target output points"
        lbl_points_hint.Left = 272; lbl_points_hint.Top = y_top + 2
        lbl_points_hint.Font.Color = 0x888888

        y_top += 28

        # Overlap
        lbl_overlap = vcl.TLabel(Form)
        lbl_overlap.Parent = Form
        lbl_overlap.Caption = "Window overlap:"
        lbl_overlap.Left = 25; lbl_overlap.Top = y_top + 2

        edt_overlap = vcl.TEdit(Form)
        edt_overlap.Parent = Form
        edt_overlap.Left = 185; edt_overlap.Top = y_top
        edt_overlap.Width = 60; edt_overlap.Text = "0"

        lbl_overlap_hint = vcl.TLabel(Form)
        lbl_overlap_hint.Parent = Form
        lbl_overlap_hint.Caption = "% (0 = no overlap, max 90)"
        lbl_overlap_hint.Left = 252; lbl_overlap_hint.Top = y_top + 2
        lbl_overlap_hint.Font.Color = 0x888888

        y_top += 30

        # ── Statistics options ───────────────────────────────────────────────
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10; sep4.Top = y_top; sep4.Width = 500; sep4.Height = 2
        sep4.Shape = "bsTopLine"
        y_top += 8

        lbl_stats = vcl.TLabel(Form)
        lbl_stats.Parent = Form
        lbl_stats.Caption = "Envelope type & statistics:"
        lbl_stats.Left = 15; lbl_stats.Top = y_top
        lbl_stats.Font.Style = {"fsBold"}
        y_top += 22

        # Percentiles
        lbl_pct_lo = vcl.TLabel(Form)
        lbl_pct_lo.Parent = Form
        lbl_pct_lo.Caption = "Lower percentile:"
        lbl_pct_lo.Left = 25; lbl_pct_lo.Top = y_top + 2

        edt_pct_lo = vcl.TEdit(Form)
        edt_pct_lo.Parent = Form
        edt_pct_lo.Left = 185; edt_pct_lo.Top = y_top
        edt_pct_lo.Width = 60; edt_pct_lo.Text = "0"

        lbl_pct_lo_hint = vcl.TLabel(Form)
        lbl_pct_lo_hint.Parent = Form
        lbl_pct_lo_hint.Caption = "% (0 = absolute min)"
        lbl_pct_lo_hint.Left = 252; lbl_pct_lo_hint.Top = y_top + 2
        lbl_pct_lo_hint.Font.Color = 0x888888

        y_top += 26

        lbl_pct_hi = vcl.TLabel(Form)
        lbl_pct_hi.Parent = Form
        lbl_pct_hi.Caption = "Upper percentile:"
        lbl_pct_hi.Left = 25; lbl_pct_hi.Top = y_top + 2

        edt_pct_hi = vcl.TEdit(Form)
        edt_pct_hi.Parent = Form
        edt_pct_hi.Left = 185; edt_pct_hi.Top = y_top
        edt_pct_hi.Width = 60; edt_pct_hi.Text = "100"

        lbl_pct_hi_hint = vcl.TLabel(Form)
        lbl_pct_hi_hint.Parent = Form
        lbl_pct_hi_hint.Caption = "% (100 = absolute max)"
        lbl_pct_hi_hint.Left = 252; lbl_pct_hi_hint.Top = y_top + 2
        lbl_pct_hi_hint.Font.Color = 0x888888

        y_top += 26

        # Mean curve checkbox
        chk_mean = vcl.TCheckBox(Form)
        chk_mean.Parent = Form
        chk_mean.Caption = "Also plot mean curve per period"
        chk_mean.Left = 25; chk_mean.Top = y_top
        chk_mean.Width = 280; chk_mean.Checked = False
        y_top += 26

        # X position
        lbl_xpos = vcl.TLabel(Form)
        lbl_xpos.Parent = Form
        lbl_xpos.Caption = "Envelope point X:"
        lbl_xpos.Left = 25; lbl_xpos.Top = y_top + 2

        cb_xpos = vcl.TComboBox(Form)
        cb_xpos.Parent = Form
        cb_xpos.Left = 185; cb_xpos.Top = y_top
        cb_xpos.Width = 160; cb_xpos.Style = "csDropDownList"
        cb_xpos.Items.Add("Center of window")
        cb_xpos.Items.Add("Start of window")
        cb_xpos.Items.Add("End of window")
        cb_xpos.ItemIndex = 0
        y_top += 26

        # Smoothing
        lbl_smooth = vcl.TLabel(Form)
        lbl_smooth.Parent = Form
        lbl_smooth.Caption = "Post-smooth window:"
        lbl_smooth.Left = 25; lbl_smooth.Top = y_top + 2

        edt_smooth = vcl.TEdit(Form)
        edt_smooth.Parent = Form
        edt_smooth.Left = 185; edt_smooth.Top = y_top
        edt_smooth.Width = 60; edt_smooth.Text = "1"

        lbl_smooth_hint = vcl.TLabel(Form)
        lbl_smooth_hint.Parent = Form
        lbl_smooth_hint.Caption = "points  (1 = off)"
        lbl_smooth_hint.Left = 252; lbl_smooth_hint.Top = y_top + 2
        lbl_smooth_hint.Font.Color = 0x888888

        y_top += 30

        # ── Shading band ──────────────────────────────────────────────────────
        sep_shade = vcl.TBevel(Form)
        sep_shade.Parent = Form
        sep_shade.Left = 10; sep_shade.Top = y_top; sep_shade.Width = 500; sep_shade.Height = 2
        sep_shade.Shape = "bsTopLine"
        y_top += 8

        chk_shading = vcl.TCheckBox(Form)
        chk_shading.Parent = Form
        chk_shading.Caption = "Add shading band (between max & min envelopes)"
        chk_shading.Left = 15; chk_shading.Top = y_top
        chk_shading.Width = 380; chk_shading.Checked = False
        y_top += 26

        lbl_shading_color = vcl.TLabel(Form)
        lbl_shading_color.Parent = Form
        lbl_shading_color.Caption = "Shading color:"
        lbl_shading_color.Left = 25; lbl_shading_color.Top = y_top + 3

        # Prefer a TColorBox picker; fall back to a hex TEdit if unavailable.
        clr_shading_is_edit = [False]
        try:
            clr_shading = vcl.TColorBox(Form)
            clr_shading.Parent = Form
            clr_shading.Left = 185; clr_shading.Top = y_top
            clr_shading.Width = 120
            clr_shading.Style = "cbStandardColors,cbExtendedColors,cbSystemColors"
            clr_shading.Selected = 0xC0C0C0
        except Exception:
            clr_shading_is_edit[0] = True
            clr_shading = vcl.TEdit(Form)
            clr_shading.Parent = Form
            clr_shading.Left = 185; clr_shading.Top = y_top
            clr_shading.Width = 80; clr_shading.Text = "C0C0C0"

        lbl_shading_hint = vcl.TLabel(Form)
        lbl_shading_hint.Parent = Form
        lbl_shading_hint.Caption = "(solid fill, default light-gray)"
        lbl_shading_hint.Left = 315 if not clr_shading_is_edit[0] else 275
        lbl_shading_hint.Top = y_top + 3
        lbl_shading_hint.Font.Color = 0x888888

        y_top += 32

        # ── Radio button mutual exclusion ────────────────────────────────────
        def on_rb_time(Sender):
            edt_time.Enabled = True
            edt_sample.Enabled = False
            edt_points.Enabled = False

        def on_rb_sample(Sender):
            edt_time.Enabled = False
            edt_sample.Enabled = True
            edt_points.Enabled = False

        def on_rb_points(Sender):
            edt_time.Enabled = False
            edt_sample.Enabled = False
            edt_points.Enabled = True
            _update_defaults()

        rb_time.OnClick   = on_rb_time
        rb_sample.OnClick = on_rb_sample
        rb_points.OnClick = on_rb_points

        # ── Help panel ───────────────────────────────────────────────────────
        sep5 = vcl.TBevel(Form)
        sep5.Parent = Form
        sep5.Left = 10; sep5.Top = y_top; sep5.Width = 500; sep5.Height = 2
        sep5.Shape = "bsTopLine"
        y_top += 6

        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 10; help_panel.Top = y_top
        help_panel.Width = 500; help_panel.Height = 56
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0

        lbl_help = vcl.TLabel(Form)
        lbl_help.Parent = help_panel
        lbl_help.Caption = (
            "Period default = x_range / 1000  -->  ~ 1000 envelope points.\n"
            "Overlap > 0: smoother curves, more output points.\n"
            "Memory usage: O(period_size x columns) only — file never fully loaded."
        )
        lbl_help.Left = 8; lbl_help.Top = 6
        lbl_help.Font.Color = 0x804000

        y_top += 62

        # ── Buttons ──────────────────────────────────────────────────────────
        sep6 = vcl.TBevel(Form)
        sep6.Parent = Form
        sep6.Left = 10; sep6.Top = y_top; sep6.Width = 500; sep6.Height = 2
        sep6.Shape = "bsTopLine"
        y_top += 8

        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Plot Envelope"
        btn_ok.ModalResult = 1
        btn_ok.Default = True
        btn_ok.Left = 145; btn_ok.Top = y_top
        btn_ok.Width = 130; btn_ok.Height = 28

        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        btn_cancel.Left = 290; btn_cancel.Top = y_top
        btn_cancel.Width = 100; btn_cancel.Height = 28

        Form.Height = y_top + 60

        # ── Detect columns closure ───────────────────────────────────────────
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
                    sep = _detect_separator(file_path, has_header, skip_rows_val)
                elif sep_idx == 1:
                    sep = ','
                elif sep_idx == 2:
                    sep = ';'
                elif sep_idx == 3:
                    sep = '\t'
                else:
                    sep = '|'

                headers, col_types, n_cols = _detect_column_types(
                    file_path, has_header, sep, skip_rows_val)

                # Clear old checkboxes
                for chk, _, __ in column_checkboxes:
                    chk.Free()
                column_checkboxes = []

                # Rebuild X combo
                cb_x_column.Items.Clear()
                cb_x_column.Items.Add("(none — use row index)")
                x_map = [(None, None)]  # index 0 = none

                chk_top = 5
                for i, (hdr, ctype) in enumerate(zip(headers, col_types)):
                    if ctype == 'ignore':
                        chk = vcl.TCheckBox(Form)
                        chk.Parent = scroll_box
                        chk.Left = 8; chk.Top = chk_top
                        chk.Width = 470
                        chk.Caption = f"{hdr}  [text — ignored]"
                        chk.Checked = False; chk.Enabled = False
                        chk.Font.Color = 0x888888
                        column_checkboxes.append((chk, i, hdr))
                        chk_top += 22
                        continue

                    type_tag = " [dt→s]" if ctype == 'datetime' else " [num]"
                    cb_x_column.Items.Add(f"{hdr}{type_tag}")
                    x_map.append((i, ctype))

                    if ctype == 'numeric':
                        chk = vcl.TCheckBox(Form)
                        chk.Parent = scroll_box
                        chk.Left = 8; chk.Top = chk_top
                        chk.Width = 470
                        chk.Caption = f"{hdr}{type_tag}"
                        chk.Checked = True
                        column_checkboxes.append((chk, i, hdr))
                        chk_top += 22

                cb_x_column.ItemIndex = 1 if len(x_map) > 1 else 0
                x_col_map[0] = x_map

                # Estimate X range for default period
                x_sel = cb_x_column.ItemIndex
                if x_sel > 0 and x_sel < len(x_map):
                    xi, xtype = x_map[x_sel]
                else:
                    xi, xtype = None, 'numeric'

                _approx_rows = 0
                if xi is not None:
                    try:
                        xf, xl, approx_rows, _ = _quick_scan_xrange(
                            file_path, has_header, sep, xi, xtype, skip_rows_val)
                        _approx_rows = approx_rows
                        xrange = abs(xl - xf)
                        try:
                            n_pts = max(1, int(edt_points.Text))
                        except (ValueError, TypeError):
                            n_pts = 1000
                        default_t = xrange / n_pts if xrange > 0 else 1.0
                        edt_time.Text = f"{default_t:.4g}"
                        edt_sample.Text = str(max(1, approx_rows // n_pts))
                        n_usable = sum(1 for t in col_types if t == 'numeric')
                        lbl_status.Caption = (
                            f"{n_usable} numeric cols · "
                            f"~{approx_rows} rows · "
                            f"X range ≈ {xrange:.4g}"
                        )
                        lbl_status.Font.Color = 0x008800
                    except Exception:
                        lbl_status.Caption = "Columns detected (range scan failed)"
                        lbl_status.Font.Color = 0x888800
                else:
                    lbl_status.Caption = "Columns detected"
                    lbl_status.Font.Color = 0x008800

                detected_info[0] = {
                    'headers': headers,
                    'col_types': col_types,
                    'separator': sep,
                    'n_cols': n_cols,
                    'approx_rows': _approx_rows,
                    'skip_rows': skip_rows_val,
                }
                edt_fs.Enabled = (cb_x_column.ItemIndex == 0)

            except Exception as e:
                lbl_status.Caption = f"Error: {str(e)[:40]}"
                lbl_status.Font.Color = 0x0000AA
                detected_info[0] = None

        def _update_defaults(Sender=None):
            """Recomputes edt_time and edt_sample from edt_points + current X column."""
            if not detected_info[0]:
                return
            info = detected_info[0]
            sep = info['separator']
            has_hdr = chk_header.Checked
            skip_rows_v = info.get('skip_rows', 0)
            try:
                n_pts = max(1, int(edt_points.Text))
            except (ValueError, TypeError):
                n_pts = 1000
            x_sel = cb_x_column.ItemIndex
            xmap = x_col_map[0] or [(None, None)]
            xi, xtype = None, 'numeric'
            if x_sel > 0 and x_sel < len(xmap):
                xi, xtype = xmap[x_sel]
            edt_fs.Enabled = (xi is None)
            if xi is not None:
                try:
                    xf, xl, ar, _ = _quick_scan_xrange(
                        file_path, has_hdr, sep, xi, xtype, skip_rows_v)
                    xrange_val = abs(xl - xf)
                    if xrange_val > 0:
                        edt_time.Text = f"{xrange_val / n_pts:.4g}"
                    edt_sample.Text = str(max(1, ar // n_pts))
                except Exception:
                    pass
            else:
                ar = info.get('approx_rows', 0)
                if ar > 0:
                    try:
                        fs_val = max(1e-12, float(edt_fs.Text))
                    except (ValueError, TypeError):
                        fs_val = 1.0
                    edt_time.Text = f"{ar / fs_val / n_pts:.4g}"
                    edt_sample.Text = str(max(1, ar // n_pts))

        btn_detect.OnClick = refresh_columns
        cb_x_column.OnChange = _update_defaults
        edt_points.OnChange = _update_defaults
        refresh_columns(None)   # auto-detect on open

        # ── Modal dialog ─────────────────────────────────────────────────────
        if Form.ShowModal() != 1:
            return

        # ── Collect parameters ───────────────────────────────────────────────
        if not detected_info[0]:
            show_error("Press 'Detect columns' before plotting.", "CSV Envelope")
            return

        info       = detected_info[0]
        sep        = info['separator']
        col_types  = info['col_types']
        headers    = info['headers']
        has_header = chk_header.Checked
        skip_rows  = info.get('skip_rows', 0)

        # X column
        x_sel = cb_x_column.ItemIndex
        xmap  = x_col_map[0] or [(None, None)]
        if x_sel > 0 and x_sel < len(xmap):
            x_col_idx, x_col_type = xmap[x_sel]
        else:
            x_col_idx, x_col_type = None, 'numeric'

        # Y columns
        y_col_indices = []
        y_col_names   = []
        for chk, col_idx, col_name in column_checkboxes:
            if chk.Checked and chk.Enabled:
                y_col_indices.append(col_idx)
                y_col_names.append(col_name)

        if not y_col_indices:
            show_error("Select at least one Y column.", "CSV Envelope")
            return

        # Period
        use_time_based = rb_time.Checked
        if rb_points.Checked:
            try:
                n_pts_val = max(1, int(edt_points.Text))
            except (ValueError, TypeError):
                n_pts_val = 1000
            if x_col_idx is not None and x_col_idx >= 0:
                try:
                    xf2, xl2, ar2, _ = _quick_scan_xrange(
                        file_path, has_header, sep, x_col_idx, x_col_type, skip_rows)
                    xr2 = abs(xl2 - xf2)
                    period = xr2 / n_pts_val if xr2 > 0 else 1.0
                except Exception:
                    period = 1.0
                use_time_based = True
            else:
                ar2 = info.get('approx_rows', 1000) or 1000
                period = max(1.0, ar2 / n_pts_val)
                use_time_based = False
        else:
            try:
                if use_time_based:
                    period = float(edt_time.Text)
                else:
                    period = float(edt_sample.Text)
                if period <= 0:
                    raise ValueError
            except ValueError:
                show_error("Period must be a positive number.", "CSV Envelope")
                return

        # Overlap
        try:
            overlap_frac = max(0.0, min(0.9, float(edt_overlap.Text) / 100.0))
        except ValueError:
            overlap_frac = 0.0

        # Percentiles
        try:
            pct_lo = max(0.0, min(100.0, float(edt_pct_lo.Text)))
            pct_hi = max(0.0, min(100.0, float(edt_pct_hi.Text)))
            if pct_lo >= pct_hi:
                show_error("Lower percentile must be less than upper.", "CSV Envelope")
                return
        except ValueError:
            pct_lo, pct_hi = 0.0, 100.0

        # X position
        xpos_map = {0: 'center', 1: 'start', 2: 'end'}
        x_pos = xpos_map.get(cb_xpos.ItemIndex, 'center')

        include_mean = chk_mean.Checked

        # Smooth
        try:
            smooth_window = max(1, int(edt_smooth.Text))
        except ValueError:
            smooth_window = 1

        # Sampling frequency (for row index mode)
        try:
            fs = max(1e-12, float(edt_fs.Text))
        except (ValueError, TypeError):
            fs = 1.0

        # Shading band
        add_shading = chk_shading.Checked
        if clr_shading_is_edit[0]:
            try:
                shading_color = int(
                    clr_shading.Text.strip().lstrip('#').replace('0x', ''), 16
                ) & 0xFFFFFF
            except (ValueError, TypeError):
                shading_color = 0xC0C0C0
        else:
            try:
                shading_color = safe_color(clr_shading.Selected)
            except (ValueError, TypeError, OverflowError):
                shading_color = 0xC0C0C0

        # Quick pre-check: estimate rows per period
        if x_col_idx is not None:
            try:
                xf, xl, approx_rows, first_dt_ref = _quick_scan_xrange(
                    file_path, has_header, sep, x_col_idx, x_col_type, skip_rows)
                xrange = abs(xl - xf)
                if use_time_based and xrange > 0:
                    est_rpp = approx_rows * period / xrange
                else:
                    est_rpp = period
                if est_rpp < 2:
                    msg = (
                        f"The period ({period:.4g}) may yield fewer than 2 "
                        f"rows per window (est. {est_rpp:.1f}).\n"
                        f"The envelope may be degenerate. Continue?"
                    )
                    if vcl.Application.MessageBox(msg, "CSV Envelope", 0x34) != 6:
                        return
            except Exception:
                first_dt_ref = None
        else:
            first_dt_ref = None
            x_col_idx    = None

        # ── Run computation ──────────────────────────────────────────────────
        try:
            x_pts, col_upper, col_lower, col_mean = compute_envelope(
                file_path, has_header, sep,
                x_col_idx if x_col_idx is not None else -1,
                y_col_indices,
                x_col_type,
                period, use_time_based,
                overlap_frac,
                pct_lo, pct_hi,
                x_pos,
                include_mean,
                smooth_window,
                first_datetime_ref=first_dt_ref,
                fs=fs,
                skip_rows=skip_rows,
            )
        except Exception as e:
            show_error(f"Error computing envelope:\n{str(e)}", "CSV Envelope")
            return

        if not x_pts:
            show_error("No envelope points produced. Check file and settings.", "CSV Envelope")
            return

        # ── Create series ────────────────────────────────────────────────────
        series_created = 0
        shadings_created = 0
        n_cols_y = len(y_col_indices)

        lo_label = f"p{int(pct_lo)}" if pct_lo > 0   else "min"
        hi_label = f"p{int(pct_hi)}" if pct_hi < 100 else "max"

        for i, col_name in enumerate(y_col_names):
            c_hi   = safe_color(SERIES_COLORS[(2 * i)     % 12])
            c_lo   = safe_color(SERIES_COLORS[(2 * i + 1) % 12])
            c_mean = safe_color(SERIES_COLORS[(2 * i + 2) % 12])

            curves = [
                ('upper', col_upper[i], f"{col_name} [{hi_label} env]", c_hi),
                ('lower', col_lower[i], f"{col_name} [{lo_label} env]", c_lo),
            ]
            if include_mean and col_mean is not None:
                curves.append(('mean', col_mean[i], f"{col_name} [mean]", c_mean))

            made = {}
            for role, values, legend, color in curves:
                pts = [Point(float(x), float(y))
                       for x, y in zip(x_pts, values)
                       if y is not None]
                if not pts:
                    continue
                s = Graph.TPointSeries()
                s.PointType  = Graph.ptCartesian
                s.Points     = pts
                s.LegendText = legend
                s.Size       = 0
                s.Style      = 0
                s.LineSize   = 1
                s.ShowLabels = False
                s.FillColor  = color
                s.FrameColor = color
                s.LineColor  = color
                Graph.FunctionList.append(s)
                series_created += 1
                made[role] = s

            # Optional shading band between the upper and lower envelopes.
            # A 1-period moving-average trendline turns each point series into a
            # function; a "between functions" shading is then drawn between them.
            if add_shading and 'upper' in made and 'lower' in made:
                try:
                    ma_up = made['upper'].CreateMovingAverage(1)
                    ma_lo = made['lower'].CreateMovingAverage(1)

                    # CreateMovingAverage only *returns* the function — it must
                    # be inserted into the graph explicitly (see Graph plugin
                    # docs, TPointSeries.CreateModelTrendline example).
                    Graph.FunctionList.append(ma_up)
                    Graph.FunctionList.append(ma_lo)

                    sh = Graph.TShading()
                    sh.ShadeStyle = Graph.ssBetween
                    sh.Func2      = ma_lo
                    sh.Color      = shading_color
                    # Leave Min/Max (Options From/To) and Min2/Max2 (2nd Function
                    # From/To) unset/blank — setting explicit limits prevents the
                    # "between functions" shading from drawing. Graph then shades
                    # over the full overlapping domain automatically.
                    sh.LegendText   = f"{col_name} [envelope band]"
                    sh.ShowInLegend = False
                    ma_up.ChildList.append(sh)

                    # The shading is a CHILD of the upper trendline, so that
                    # trendline must stay visible for the band to render
                    # (hiding it would hide the band too). Keep both trendlines
                    # visible but styled to overlap the existing envelope curves
                    # exactly — color-matched hairline, no legend entry — so no
                    # duplicate curve is perceptible.
                    ma_up.Color = c_hi
                    ma_lo.Color = c_lo
                    for ma in (ma_up, ma_lo):
                        ma.ShowInLegend = False
                        try:
                            ma.Size = 0      # hairline; Graph may clamp to 1px
                        except Exception:
                            pass

                    shadings_created += 1
                except Exception as e:
                    show_error(
                        f"Could not create shading band for '{col_name}':\n{str(e)}",
                        "CSV Envelope")

        Graph.Update()

        graph_title = edt_graph_title.Text.strip()
        if graph_title:
            Graph.Axes.Title = graph_title
            Graph.Update()

        stats_lines = [f"  {n}: {len(x_pts)} pts" for n in y_col_names]
        shading_line = f"Shading bands: {shadings_created}\n" if add_shading else ""
        show_info(
            f"Envelope plotted.\n\n"
            f"File: {os.path.basename(file_path)}\n"
            f"Series created: {series_created}\n"
            f"{shading_line}"
            f"Envelope points: {len(x_pts)}\n"
            f"Period: {period:.4g} {'s' if use_time_based else ' rows'}"
            f"{'  overlap: ' + str(int(overlap_frac*100)) + '%' if overlap_frac > 0 else ''}\n"
            f"Percentiles: {int(pct_lo)}%–{int(pct_hi)}%"
            f"{'  + mean' if include_mean else ''}",
            "CSV Envelope"
        )

    finally:
        Form.Free()


# ─── Menu registration ────────────────────────────────────────────────────────

_icon_path = os.path.join(os.path.dirname(__file__), "CSVEnvelope_sm.png")

CSVEnvelopeAction = Graph.CreateAction(
    Caption="CSV Envelope...",
    OnExecute=plot_envelope,
    Hint="Plots streaming max/min envelope curves from CSV files (low memory).",
    ShortCut="",
    IconFile=_icon_path if os.path.exists(_icon_path) else "",
)

Graph.AddActionToMainMenu(
    CSVEnvelopeAction,
    TopMenu="Plugins",
    SubMenus=["Graphîa", "Import/Export"],
)
