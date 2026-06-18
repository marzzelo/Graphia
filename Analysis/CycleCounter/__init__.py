# Analysis/CycleCounter/__init__.py
import os
from common import (
    get_selected_point_series, show_error, show_info,
    get_series_stats, Graph, vcl, Point, safe_color
)

PluginName = "Cycle Counter"
PluginVersion = "1.1"
PluginDescription = (
    "Counts signal crossings through a threshold level with hysteresis. "
    "Selectable counting edge (ascending / descending) and configurable "
    "hysteresis band suppress noise-induced false counts. "
    "Adds a statistics annotation and optional crossing markers to the graph."
)


# ── RTF builder ───────────────────────────────────────────────────────────────

def _make_rtf(bold_title, body_lines):
    """
    Build a valid RTF string for Graph.TTextLabel.

    bold_title  – first line, rendered in bold.
    body_lines  – subsequent lines, regular weight.
    Non-ASCII characters are encoded as RTF \\uN? escapes.
    """
    def esc(s):
        s = s.replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}')
        out = []
        for ch in s:
            if ord(ch) < 128:
                out.append(ch)
            else:
                n = ord(ch)
                if n > 32767:
                    n -= 65536          # RTF uses signed 16-bit
                out.append(f'\\u{n}?')
        return ''.join(out)

    parts = [
        r'{\rtf1\ansi\deff0',
        r'{\fonttbl{\f0\fswiss\fcharset0 Arial;}}',
        r'\pard\sb0\sa0\f0\fs18',
        r'\b ', esc(bold_title), r'\b0\par',
    ]
    for line in body_lines:
        parts += [r'\pard\sb0\sa0\fs18 ', esc(line), r'\par']
    parts.append('}')
    return ''.join(parts)


# ── Crossing algorithm ────────────────────────────────────────────────────────

def _interpolate_crossing(x0, y0, x1, y1, threshold):
    """Linear interpolation to find the x where the signal crosses threshold."""
    if y1 == y0:
        return x0
    return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)


def _count_crossings(x_vals, y_vals, level, edge, band, x_from, x_to):
    """
    Count threshold crossings with hysteresis within [x_from, x_to].

    Ascending:  arm when y < (level - band/2),
                count when y > (level + band/2) after arming.
    Descending: arm when y > (level + band/2),
                count when y < (level - band/2) after arming.

    Returns a list of (x_crossing, level) tuples.
    """
    lower = level - band / 2.0
    upper = level + band / 2.0

    filtered = [(x, y) for x, y in zip(x_vals, y_vals) if x_from <= x <= x_to]
    if len(filtered) < 2:
        return []

    crossings = []
    first_y = filtered[0][1]

    if edge == 'ascending':
        armed = first_y < lower
        for i in range(1, len(filtered)):
            x, y = filtered[i]
            px, py = filtered[i - 1]
            if y < lower:
                armed = True
            elif armed and y > upper:
                crossings.append((_interpolate_crossing(px, py, x, y, upper), level))
                armed = False

    else:  # descending
        armed = first_y > upper
        for i in range(1, len(filtered)):
            x, y = filtered[i]
            px, py = filtered[i - 1]
            if y > upper:
                armed = True
            elif armed and y < lower:
                crossings.append((_interpolate_crossing(px, py, x, y, lower), level))
                armed = False

    return crossings


# ── Plugin callback ───────────────────────────────────────────────────────────

def count_cycles(Action):
    """Counts threshold crossings on the selected point series."""

    point_series, error_msg = get_selected_point_series()
    if point_series is None:
        show_error(error_msg, "Cycle Counter")
        return

    points = point_series.Points
    if not points or len(points) < 2:
        show_error("The series must have at least 2 points.", "Cycle Counter")
        return

    stats = get_series_stats(point_series)
    x_min, x_max = stats['x_min'], stats['x_max']
    y_min, y_max = stats['y_min'], stats['y_max']
    y_mid = (y_min + y_max) / 2.0
    band_default = (y_max - y_min) * 0.05  # 5 % of amplitude range

    Form = vcl.TForm(None)
    try:
        Form.Caption = "Cycle Counter"
        Form.Width = 420
        Form.Height = 460
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"

        lbl_refs = []  # keep label references alive

        # ── Series info ───────────────────────────────────────────────────────
        lbl = vcl.TLabel(Form); lbl.Parent = Form
        lbl.Caption = f"Series: {point_series.LegendText}   ({len(points)} points)"
        lbl.Left = 20; lbl.Top = 15
        lbl.Font.Style = {"fsBold"}
        lbl_refs.append(lbl)

        lbl = vcl.TLabel(Form); lbl.Parent = Form
        lbl.Caption = f"X: [{x_min:.4g}, {x_max:.4g}]     Y: [{y_min:.4g}, {y_max:.4g}]"
        lbl.Left = 20; lbl.Top = 35
        lbl.Font.Color = 0x666666
        lbl_refs.append(lbl)

        sep = vcl.TBevel(Form); sep.Parent = Form
        sep.Left = 10; sep.Top = 57; sep.Width = 384; sep.Height = 2
        sep.Shape = "bsTopLine"

        # ── Threshold level ───────────────────────────────────────────────────
        lbl = vcl.TLabel(Form); lbl.Parent = Form
        lbl.Caption = "Threshold level:"; lbl.Left = 20; lbl.Top = 72
        lbl_refs.append(lbl)

        edit_level = vcl.TEdit(Form); edit_level.Parent = Form
        edit_level.Left = 210; edit_level.Top = 69; edit_level.Width = 130
        edit_level.Text = f"{y_mid:.6g}"

        # ── Counting edge ─────────────────────────────────────────────────────
        lbl = vcl.TLabel(Form); lbl.Parent = Form
        lbl.Caption = "Counting edge:"; lbl.Left = 20; lbl.Top = 102
        lbl_refs.append(lbl)

        cb_edge = vcl.TComboBox(Form); cb_edge.Parent = Form
        cb_edge.Left = 210; cb_edge.Top = 99; cb_edge.Width = 130
        cb_edge.Style = "csDropDownList"
        cb_edge.Items.Add("Ascending  ↑")
        cb_edge.Items.Add("Descending ↓")
        cb_edge.ItemIndex = 0

        # ── Hysteresis band ───────────────────────────────────────────────────
        lbl = vcl.TLabel(Form); lbl.Parent = Form
        lbl.Caption = "Hysteresis band:"; lbl.Left = 20; lbl.Top = 132
        lbl_refs.append(lbl)

        edit_band = vcl.TEdit(Form); edit_band.Parent = Form
        edit_band.Left = 210; edit_band.Top = 129; edit_band.Width = 130
        edit_band.Text = f"{band_default:.4g}"

        # ── Counting segment ──────────────────────────────────────────────────
        sep2 = vcl.TBevel(Form); sep2.Parent = Form
        sep2.Left = 10; sep2.Top = 160; sep2.Width = 384; sep2.Height = 2
        sep2.Shape = "bsTopLine"

        lbl = vcl.TLabel(Form); lbl.Parent = Form
        lbl.Caption = "Counting segment:"; lbl.Left = 20; lbl.Top = 168
        lbl.Font.Style = {"fsBold"}
        lbl_refs.append(lbl)

        lbl = vcl.TLabel(Form); lbl.Parent = Form
        lbl.Caption = "X from:"; lbl.Left = 20; lbl.Top = 193
        lbl_refs.append(lbl)

        edit_xfrom = vcl.TEdit(Form); edit_xfrom.Parent = Form
        edit_xfrom.Left = 210; edit_xfrom.Top = 190; edit_xfrom.Width = 130
        edit_xfrom.Text = f"{x_min:.6g}"

        lbl = vcl.TLabel(Form); lbl.Parent = Form
        lbl.Caption = "X to:"; lbl.Left = 20; lbl.Top = 223
        lbl_refs.append(lbl)

        edit_xto = vcl.TEdit(Form); edit_xto.Parent = Form
        edit_xto.Left = 210; edit_xto.Top = 220; edit_xto.Width = 130
        edit_xto.Text = f"{x_max:.6g}"

        # ── Info panel ────────────────────────────────────────────────────────
        sep3 = vcl.TBevel(Form); sep3.Parent = Form
        sep3.Left = 10; sep3.Top = 252; sep3.Width = 384; sep3.Height = 2
        sep3.Shape = "bsTopLine"

        panel = vcl.TPanel(Form); panel.Parent = Form
        panel.Left = 20; panel.Top = 259; panel.Width = 370; panel.Height = 76
        panel.BevelOuter = "bvLowered"; panel.Color = 0xFFF8F0

        lbl = vcl.TLabel(Form); lbl.Parent = panel
        lbl.Caption = (
            "Ascending:  arm below (level − band/2),  count above (level + band/2).\n"
            "Descending: arm above (level + band/2),  count below (level − band/2).\n"
            "Band = 0 → simple crossing counter at the threshold line."
        )
        lbl.Left = 10; lbl.Top = 10
        lbl.Font.Color = 0x804000
        lbl_refs.append(lbl)

        # ── Marker checkbox ───────────────────────────────────────────────────
        chk_mark = vcl.TCheckBox(Form); chk_mark.Parent = Form
        chk_mark.Caption = "Add crossing markers to the graph"
        chk_mark.Left = 20; chk_mark.Top = 348
        chk_mark.Width = 260; chk_mark.Checked = True

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_ok = vcl.TButton(Form); btn_ok.Parent = Form
        btn_ok.Caption = "Count"; btn_ok.ModalResult = 1; btn_ok.Default = True
        btn_ok.Left = 80; btn_ok.Top = 392; btn_ok.Width = 100; btn_ok.Height = 30

        btn_cancel = vcl.TButton(Form); btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"; btn_cancel.ModalResult = 2; btn_cancel.Cancel = True
        btn_cancel.Left = 220; btn_cancel.Top = 392; btn_cancel.Width = 100; btn_cancel.Height = 30

        if Form.ShowModal() != 1:
            return

        # ── Parse inputs ──────────────────────────────────────────────────────
        try:
            level  = float(edit_level.Text)
            band   = float(edit_band.Text)
            x_from = float(edit_xfrom.Text)
            x_to   = float(edit_xto.Text)
        except ValueError:
            show_error("Invalid numeric value in one of the fields.", "Cycle Counter")
            return

        if band < 0:
            show_error("Hysteresis band must be ≥ 0.", "Cycle Counter")
            return
        if x_from >= x_to:
            show_error("X from must be strictly less than X to.", "Cycle Counter")
            return

        edge = 'ascending' if cb_edge.ItemIndex == 0 else 'descending'
        edge_label = "Ascending ↑" if edge == 'ascending' else "Descending ↓"
        add_markers = chk_mark.Checked

    finally:
        Form.Free()

    # ── Count crossings ───────────────────────────────────────────────────────
    x_vals = [p.x for p in points]
    y_vals = [p.y for p in points]

    crossings = _count_crossings(x_vals, y_vals, level, edge, band, x_from, x_to)
    count     = len(crossings)

    lower  = level - band / 2.0
    upper  = level + band / 2.0
    x_span = x_to - x_from
    rate   = count / x_span if (count >= 1 and x_span > 0) else 0.0

    signal_name = point_series.LegendText or "Signal"

    # ── Crossing positions info dialog (only when there are crossings) ─────────
    if count > 0:
        pos_lines = []
        shown = min(count, 30)
        if count > 30:
            pos_lines.append(f"First {shown} of {count} crossing positions (x):")
        else:
            pos_lines.append(f"Crossing positions (x)  [×{count} total]:")
        pos_lines += [f"  [{i+1:2d}]  {cx:.6g}" for i, (cx, _) in enumerate(crossings[:30])]
        show_info("\n".join(pos_lines), "Cycle Counter")

    # ── Statistics text box on the graph ──────────────────────────────────────
    rate_str   = f"{rate:.4g} Hz" if count >= 1 else "N/A"
    hyst_range = f"[{lower:.4g} ↔ {upper:.4g}]"

    box_title = f"{signal_name} - Cycle Counting Statistics"
    box_body  = [
        f"Crossings counted:  {count}",
        f"Avg. crossing rate: {rate_str}",
        f"Threshold level:    {level:.4g}",
        f"Hysteresis band:    {band:.4g}  {hyst_range}",
        f"Segment:            [{x_from:.4g}, {x_to:.4g}]",
        f"Counting edge:      {edge_label}",
    ]

    try:
        txt = Graph.TTextLabel()
        txt.Text            = _make_rtf(box_title, box_body)
        txt.BackgroundColor = 0xDCF8FF  # Cornsilk (R=255, G=248, B=220) in TColor/BGR
        txt.Placement       = Graph.lpUserTopLeft
        txt.Pos             = (x_from, y_max)
        txt.Rotation        = 0
        Graph.FunctionList.append(txt)
    except Exception as e:
        # Fallback: show a simple info dialog if TTextLabel is unavailable
        show_info(box_title + "\n" + "\n".join(box_body), "Cycle Counter - Statistics")

    # ── Optional crossing marker series ───────────────────────────────────────
    if add_markers and count > 0:
        # Label format:  "SignalName | ×count | 0.6Hz"
        rate_tag  = f" | {rate:.3g}Hz" if count >= 1 else ""
        ms_legend = f"{signal_name} | ×{count}{rate_tag}"

        ms = Graph.TPointSeries()
        ms.Points    = [Point(cx, cy) for cx, cy in crossings]
        ms.LegendText = ms_legend
        ms.PointType  = Graph.ptCartesian
        ms.Size       = 7
        ms.Style      = 4       # diamond / cross marker
        ms.LineSize   = 0
        ms.ShowLabels = False
        col = safe_color(0x0000CC)  # dark red in BGR = #CC0000
        ms.FillColor = col; ms.FrameColor = col; ms.LineColor = col
        Graph.FunctionList.append(ms)

    Graph.Update()


# ── Menu registration ─────────────────────────────────────────────────────────
_icon = os.path.join(os.path.dirname(__file__), "CycleCounter_sm.png")
_action_kwargs = {
    'Caption'  : "Cycle Counter...",
    'OnExecute': count_cycles,
    'Hint'     : "Counts threshold crossings with hysteresis on the selected series.",
    'ShortCut' : ""
}
if os.path.exists(_icon):
    _action_kwargs['IconFile'] = _icon

CycleCounterAction = Graph.CreateAction(**_action_kwargs)

Graph.AddActionToMainMenu(
    CycleCounterAction, TopMenu="Plugins", SubMenus=["Graph\xeea", "Analysis"]
)
