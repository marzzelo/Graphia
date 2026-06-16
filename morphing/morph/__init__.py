"""
Morph - Plugin to transform point series to new limits
Allows scaling, translating, and aligning one or more series.
"""

import Graph
import vcl  # type: ignore
import os

from common import (setup_venv, get_selected_point_series, show_error, show_info,
                    get_series_data, Point, safe_color, get_visible_point_series)

import numpy as np


def morph_series(Action):
    series, error = get_selected_point_series()
    if series is None:
        show_error(error, "Morph")
        return

    x_vals, y_vals = get_series_data(series)
    if not y_vals:
        show_info("The selected series has no points.", "Morph")
        return

    x_arr = np.array(x_vals)
    y_arr = np.array(y_vals)

    ref_xmin = float(np.min(x_arr))
    ref_xmax = float(np.max(x_arr))
    ref_ymin = float(np.min(y_arr))
    ref_ymax = float(np.max(y_arr))
    ref_ymid = (ref_ymin + ref_ymax) / 2.0

    visible_xmin = Graph.Axes.xAxis.Min
    visible_xmax = Graph.Axes.xAxis.Max
    visible_ymin = Graph.Axes.yAxis.Min
    visible_ymax = Graph.Axes.yAxis.Max

    visible_series = get_visible_point_series()

    Form = vcl.TForm(None)
    try:
        Form.Caption = "Morph - Transform Series"
        Form.Width = 440
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"

        _refs = []  # keep widget references alive

        def make_label(caption, left, top, bold=False, color=None):
            w = vcl.TLabel(Form)
            w.Parent = Form
            w.Caption = caption
            w.Left = left
            w.Top = top
            if bold:
                w.Font.Style = {"fsBold"}
            if color is not None:
                w.Font.Color = color
            _refs.append(w)
            return w

        def sep(y):
            w = vcl.TBevel(Form)
            w.Parent = Form
            w.Left = 10
            w.Top = y
            w.Width = 410
            w.Height = 2
            w.Shape = "bsTopLine"
            _refs.append(w)
            return y + 10

        def section_checkbox(caption, y, checked=True):
            """Section header with enable/disable checkbox."""
            chk = vcl.TCheckBox(Form)
            chk.Parent = Form
            chk.Left = 10
            chk.Top = y
            chk.Caption = "  " + caption
            chk.Checked = checked
            chk.Font.Style = {"fsBold"}
            chk.Width = 220
            _refs.append(chk)
            return chk, y + 24

        def field_row(caption, default, hint, y, controls=None):
            """Label + TEdit row; appends all widgets to controls list if given."""
            lw = make_label(caption, 20, y + 5)
            edt = vcl.TEdit(Form)
            edt.Parent = Form
            edt.Left = 90
            edt.Top = y
            edt.Width = 115
            edt.Text = default
            _refs.append(edt)
            if controls is not None:
                controls.append(lw)
                controls.append(edt)
            if hint:
                hw = make_label(hint, 215, y + 5, color=0x888888)
                if controls is not None:
                    controls.append(hw)
            return edt, y + 28

        def set_enabled(controls, enabled):
            for w in controls:
                w.Enabled = enabled

        # ── Header ─────────────────────────────────────────────
        make_label("Define transformations for the series", 20, 15, bold=True)
        ref_name = series.LegendText or "selected series"
        make_label(f"Reference: {ref_name}", 20, 36, color=0x666666)

        y = 60

        # ── SCALE ──────────────────────────────────────────────
        y = sep(y)
        chk_scale, y = section_checkbox("SCALE", y, checked=True)
        scale_ctl = []
        edt_xmin, y = field_row("Xmin:", f"{visible_xmin:.6g}", f"(current: {ref_xmin:.4g})", y, scale_ctl)
        edt_xmax, y = field_row("Xmax:", f"{visible_xmax:.6g}", f"(current: {ref_xmax:.4g})", y, scale_ctl)
        edt_ymin, y = field_row("Ymin:", f"{visible_ymin:.6g}", f"(current: {ref_ymin:.4g})", y, scale_ctl)
        edt_ymax, y = field_row("Ymax:", f"{visible_ymax:.6g}", f"(current: {ref_ymax:.4g})", y, scale_ctl)
        y += 8

        def on_chk_scale(Sender):
            set_enabled(scale_ctl, chk_scale.Checked)

        chk_scale.OnClick = on_chk_scale

        # ── TRANSLATE X ────────────────────────────────────────
        y = sep(y)
        chk_tx, y = section_checkbox("TRANSLATE X", y, checked=False)
        tx_ctl = []

        tx_ctl.append(make_label("Anchor:", 20, y + 4))

        pnl_tx = vcl.TPanel(Form)
        pnl_tx.Parent = Form
        pnl_tx.Left = 90
        pnl_tx.Top = y
        pnl_tx.Width = 240
        pnl_tx.Height = 24
        pnl_tx.BevelOuter = "bvNone"
        tx_ctl.append(pnl_tx)

        rb_tx_xmin = vcl.TRadioButton(Form)
        rb_tx_xmin.Parent = pnl_tx
        rb_tx_xmin.Caption = f"Xmin  ({ref_xmin:.4g})"
        rb_tx_xmin.Left = 0
        rb_tx_xmin.Top = 2
        rb_tx_xmin.Width = 120
        rb_tx_xmin.Checked = True
        tx_ctl.append(rb_tx_xmin)

        rb_tx_xmax = vcl.TRadioButton(Form)
        rb_tx_xmax.Parent = pnl_tx
        rb_tx_xmax.Caption = f"Xmax  ({ref_xmax:.4g})"
        rb_tx_xmax.Left = 122
        rb_tx_xmax.Top = 2
        rb_tx_xmax.Width = 118
        tx_ctl.append(rb_tx_xmax)

        y += 28
        edt_tx_target, y = field_row("Target X:", "0", None, y, tx_ctl)
        y += 8

        def on_tx_radio(Sender):
            if rb_tx_xmin.Checked:
                edt_tx_target.Text = "0"
            else:
                edt_tx_target.Text = f"{ref_xmax - ref_xmin:.6g}"

        rb_tx_xmin.OnClick = on_tx_radio
        rb_tx_xmax.OnClick = on_tx_radio

        set_enabled(tx_ctl, False)

        def on_chk_tx(Sender):
            set_enabled(tx_ctl, chk_tx.Checked)

        chk_tx.OnClick = on_chk_tx

        # ── TRANSLATE Y ────────────────────────────────────────
        y = sep(y)
        chk_ty, y = section_checkbox("TRANSLATE Y", y, checked=False)
        ty_ctl = []

        ty_ctl.append(make_label("Anchor:", 20, y + 4))

        pnl_ty = vcl.TPanel(Form)
        pnl_ty.Parent = Form
        pnl_ty.Left = 90
        pnl_ty.Top = y
        pnl_ty.Width = 310
        pnl_ty.Height = 24
        pnl_ty.BevelOuter = "bvNone"
        ty_ctl.append(pnl_ty)

        rb_ty_ymax = vcl.TRadioButton(Form)
        rb_ty_ymax.Parent = pnl_ty
        rb_ty_ymax.Caption = f"Ymax  ({ref_ymax:.4g})"
        rb_ty_ymax.Left = 0
        rb_ty_ymax.Top = 2
        rb_ty_ymax.Width = 100
        ty_ctl.append(rb_ty_ymax)

        rb_ty_ymin = vcl.TRadioButton(Form)
        rb_ty_ymin.Parent = pnl_ty
        rb_ty_ymin.Caption = f"Ymin  ({ref_ymin:.4g})"
        rb_ty_ymin.Left = 103
        rb_ty_ymin.Top = 2
        rb_ty_ymin.Width = 100
        rb_ty_ymin.Checked = True
        ty_ctl.append(rb_ty_ymin)

        rb_ty_ymid = vcl.TRadioButton(Form)
        rb_ty_ymid.Parent = pnl_ty
        rb_ty_ymid.Caption = f"Ymid  ({ref_ymid:.4g})"
        rb_ty_ymid.Left = 206
        rb_ty_ymid.Top = 2
        rb_ty_ymid.Width = 100
        ty_ctl.append(rb_ty_ymid)

        y += 28
        edt_ty_target, y = field_row("Target Y:", f"{ref_ymin:.6g}", None, y, ty_ctl)
        y += 8

        def on_ty_radio(Sender):
            if rb_ty_ymax.Checked:
                edt_ty_target.Text = f"{ref_ymax:.6g}"
            elif rb_ty_ymin.Checked:
                edt_ty_target.Text = f"{ref_ymin:.6g}"
            else:
                edt_ty_target.Text = f"{ref_ymid:.6g}"

        rb_ty_ymax.OnClick = on_ty_radio
        rb_ty_ymin.OnClick = on_ty_radio
        rb_ty_ymid.OnClick = on_ty_radio

        set_enabled(ty_ctl, False)

        def on_chk_ty(Sender):
            set_enabled(ty_ctl, chk_ty.Checked)

        chk_ty.OnClick = on_chk_ty

        # ── TARGET ─────────────────────────────────────────────
        y = sep(y)
        make_label("TARGET", 20, y, bold=True)
        y += 22

        scroll_height = min(len(visible_series) * 25 + 4, 120)
        scroll_box = vcl.TScrollBox(Form)
        scroll_box.Parent = Form
        scroll_box.Left = 10
        scroll_box.Top = y
        scroll_box.Width = 410
        scroll_box.Height = scroll_height
        scroll_box.BorderStyle = "bsNone"
        _refs.append(scroll_box)

        series_checks = []
        for i, vs in enumerate(visible_series):
            chk = vcl.TCheckBox(scroll_box)
            chk.Parent = scroll_box
            chk.Left = 10
            chk.Top = i * 25 + 2
            chk.Width = 385
            chk.Caption = vs.LegendText if vs.LegendText else f"Series {i + 1}"
            chk.Checked = (vs == series)
            series_checks.append((chk, vs))

        y += scroll_height + 8

        # ── OUTPUT ─────────────────────────────────────────────
        y = sep(y)
        make_label("OUTPUT", 20, y, bold=True)
        y += 22

        pnl_out = vcl.TPanel(Form)
        pnl_out.Parent = Form
        pnl_out.Left = 10
        pnl_out.Top = y
        pnl_out.Width = 410
        pnl_out.Height = 24
        pnl_out.BevelOuter = "bvNone"
        _refs.append(pnl_out)

        rb_new = vcl.TRadioButton(Form)
        rb_new.Parent = pnl_out
        rb_new.Caption = "Create new series  (same color as original)"
        rb_new.Left = 10
        rb_new.Top = 2
        rb_new.Width = 260
        rb_new.Checked = True

        rb_replace = vcl.TRadioButton(Form)
        rb_replace.Parent = pnl_out
        rb_replace.Caption = "Replace original"
        rb_replace.Left = 275
        rb_replace.Top = 2
        rb_replace.Width = 130

        y += 38

        # ── Buttons ────────────────────────────────────────────
        btn_morph = vcl.TButton(Form)
        btn_morph.Parent = Form
        btn_morph.Caption = "Morph!"
        btn_morph.Left = 115
        btn_morph.Top = y
        btn_morph.Width = 85
        btn_morph.Height = 30

        btn_close = vcl.TButton(Form)
        btn_close.Parent = Form
        btn_close.Caption = "Close"
        btn_close.ModalResult = 2
        btn_close.Cancel = True
        btn_close.Left = 215
        btn_close.Top = y
        btn_close.Width = 85
        btn_close.Height = 30

        Form.Height = y + 60

        # ── Morph logic ────────────────────────────────────────
        def on_morph_click(Sender):
            scale_on = chk_scale.Checked
            tx_on = chk_tx.Checked
            ty_on = chk_ty.Checked

            if not scale_on and not tx_on and not ty_on:
                show_error("Enable at least one transformation.", "Morph")
                return

            # Scale factors — identity if SCALE is disabled
            kx, offset_x, ky, offset_y = 1.0, 0.0, 1.0, 0.0

            if scale_on:
                try:
                    new_xmin = float(edt_xmin.Text)
                    new_xmax = float(edt_xmax.Text)
                    new_ymin = float(edt_ymin.Text)
                    new_ymax = float(edt_ymax.Text)
                except ValueError:
                    show_error("Please enter valid numeric values in the SCALE section.", "Morph")
                    return

                if new_xmax <= new_xmin:
                    show_error("Scale Xmax must be greater than Xmin.", "Morph")
                    return
                if new_ymax <= new_ymin:
                    show_error("Scale Ymax must be greater than Ymin.", "Morph")
                    return

                x_range = ref_xmax - ref_xmin
                y_range = ref_ymax - ref_ymin
                if x_range == 0:
                    show_error("Reference X range is zero. Cannot scale.", "Morph")
                    return
                if y_range == 0:
                    show_error("Reference Y range is zero. Cannot scale.", "Morph")
                    return

                kx = (new_xmax - new_xmin) / x_range
                offset_x = new_xmin - kx * ref_xmin
                ky = (new_ymax - new_ymin) / y_range
                offset_y = new_ymin - ky * ref_ymin

            # Parse Translate X target
            tx_target = 0.0
            tx_use_xmin = rb_tx_xmin.Checked
            if tx_on:
                try:
                    tx_target = float(edt_tx_target.Text)
                except ValueError:
                    show_error("Please enter a valid numeric value for Target X.", "Morph")
                    return

            # Parse Translate Y target
            ty_target = 0.0
            ty_use_ymax = rb_ty_ymax.Checked
            ty_use_ymin = rb_ty_ymin.Checked
            if ty_on:
                try:
                    ty_target = float(edt_ty_target.Text)
                except ValueError:
                    show_error("Please enter a valid numeric value for Target Y.", "Morph")
                    return

            targets = [(chk, s) for chk, s in series_checks if chk.Checked]
            if not targets:
                show_error("Select at least one series in the TARGET section.", "Morph")
                return

            for _, tgt in targets:
                t_x, t_y = get_series_data(tgt)
                if not t_x:
                    continue

                t_x_arr = np.array(t_x)
                t_y_arr = np.array(t_y)

                # Per-series translate: each series' own anchor moves to the target
                per_tx = 0.0
                if tx_on:
                    anchor_x = float(np.min(t_x_arr)) if tx_use_xmin else float(np.max(t_x_arr))
                    per_tx = tx_target - (kx * anchor_x + offset_x)

                per_ty = 0.0
                if ty_on:
                    if ty_use_ymax:
                        anchor_y = float(np.max(t_y_arr))
                    elif ty_use_ymin:
                        anchor_y = float(np.min(t_y_arr))
                    else:
                        anchor_y = (float(np.min(t_y_arr)) + float(np.max(t_y_arr))) / 2.0
                    per_ty = ty_target - (ky * anchor_y + offset_y)

                new_pts = [
                    Point(kx * p.x + offset_x + per_tx,
                          ky * p.y + offset_y + per_ty)
                    for p in tgt.Points
                ]

                if rb_new.Checked:
                    ns = Graph.TPointSeries()
                    ns.PointType = tgt.PointType
                    ns.Points = new_pts
                    ns.LegendText = f"{tgt.LegendText} [morphed]"
                    ns.Size = tgt.Size
                    ns.Style = tgt.Style
                    ns.LineSize = tgt.LineSize
                    ns.ShowLabels = tgt.ShowLabels
                    orig_color = safe_color(tgt.LineColor)
                    ns.FillColor = orig_color
                    ns.FrameColor = orig_color
                    ns.LineColor = orig_color
                    Graph.FunctionList.append(ns)
                else:
                    tgt.Points = new_pts

            Graph.Redraw()

        btn_morph.OnClick = on_morph_click
        Form.ShowModal()

    finally:
        Form.Free()


Action = Graph.CreateAction(
    Caption="Morph...",
    OnExecute=morph_series,
    Hint="Transform the selected series to new X and Y limits",
    IconFile=os.path.join(os.path.dirname(__file__), "Morph_sm.png")
)

Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Morphing"])  # type: ignore
