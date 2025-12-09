# Plugin to generate Gaussian modulated sinusoid pulses using scipy.signal.gausspulse
import sys
import os

# Add virtual environment to path to find scipy/numpy
venv_site_packages = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".venv", "Lib", "site-packages")
if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
    sys.path.append(venv_site_packages)

import Graph
import vcl
import numpy as np
from scipy import signal
from collections import namedtuple

PluginName = "Gauss Pulse Generator"
PluginVersion = "1.0"
PluginDescription = "Generates Gaussian modulated sinusoid pulses using scipy.signal.gausspulse."


def GaussPulseDialog(Action):
    """
    Opens a dialog to configure and generate Gaussian modulated sinusoid pulses.
    """
    # Create form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Gauss Pulse Generator"
        Form.Width = 480
        Form.Height = 540
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"

        inputs = {}
        labels = []  # Keep references to prevent GC

        # =====================================================================
        # Help panel at top
        # =====================================================================
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 10
        help_panel.Top = 10
        help_panel.Width = 450
        help_panel.Height = 55
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0

        lbl_help_title = vcl.TLabel(help_panel)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Gaussian Modulated Sinusoid"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        lbl_help = vcl.TLabel(help_panel)
        lbl_help.Parent = help_panel
        lbl_help.Caption = "exp(-a·t²)·exp(j·2π·fc·t)  →  yI, yQ, yenv"
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)

        # =====================================================================
        # Time Parameters Section
        # =====================================================================
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 75
        sep1.Width = 450
        sep1.Height = 2
        sep1.Shape = "bsTopLine"

        lbl_time = vcl.TLabel(Form)
        lbl_time.Parent = Form
        lbl_time.Caption = "Time Parameters"
        lbl_time.Left = 10
        lbl_time.Top = 85
        lbl_time.Font.Style = {"fsBold"}
        labels.append(lbl_time)

        # t0 (start time)
        lbl_t0 = vcl.TLabel(Form)
        lbl_t0.Parent = Form
        lbl_t0.Caption = "t₀ (start) [s]:"
        lbl_t0.Left = 20
        lbl_t0.Top = 113
        labels.append(lbl_t0)

        edt_t0 = vcl.TEdit(Form)
        edt_t0.Parent = Form
        edt_t0.Left = 120
        edt_t0.Top = 110
        edt_t0.Width = 80
        edt_t0.Text = "-1"
        inputs["t0"] = edt_t0

        # tf (end time)
        lbl_tf = vcl.TLabel(Form)
        lbl_tf.Parent = Form
        lbl_tf.Caption = "tₑ (end) [s]:"
        lbl_tf.Left = 230
        lbl_tf.Top = 113
        labels.append(lbl_tf)

        edt_tf = vcl.TEdit(Form)
        edt_tf.Parent = Form
        edt_tf.Left = 320
        edt_tf.Top = 110
        edt_tf.Width = 80
        edt_tf.Text = "1"
        inputs["tf"] = edt_tf

        # fsample
        lbl_fs = vcl.TLabel(Form)
        lbl_fs.Parent = Form
        lbl_fs.Caption = "Sample Rate [Hz]:"
        lbl_fs.Left = 20
        lbl_fs.Top = 143
        labels.append(lbl_fs)

        edt_fs = vcl.TEdit(Form)
        edt_fs.Parent = Form
        edt_fs.Left = 120
        edt_fs.Top = 140
        edt_fs.Width = 80
        edt_fs.Text = "1000"
        inputs["fs"] = edt_fs

        # =====================================================================
        # Pulse Parameters Section
        # =====================================================================
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 175
        sep2.Width = 450
        sep2.Height = 2
        sep2.Shape = "bsTopLine"

        lbl_pulse = vcl.TLabel(Form)
        lbl_pulse.Parent = Form
        lbl_pulse.Caption = "Pulse Parameters"
        lbl_pulse.Left = 10
        lbl_pulse.Top = 185
        lbl_pulse.Font.Style = {"fsBold"}
        labels.append(lbl_pulse)

        # fc (center frequency)
        lbl_fc = vcl.TLabel(Form)
        lbl_fc.Parent = Form
        lbl_fc.Caption = "fc (center freq) [Hz]:"
        lbl_fc.Left = 20
        lbl_fc.Top = 213
        labels.append(lbl_fc)

        edt_fc = vcl.TEdit(Form)
        edt_fc.Parent = Form
        edt_fc.Left = 150
        edt_fc.Top = 210
        edt_fc.Width = 80
        edt_fc.Text = "10"
        inputs["fc"] = edt_fc

        # bw (fractional bandwidth)
        lbl_bw = vcl.TLabel(Form)
        lbl_bw.Parent = Form
        lbl_bw.Caption = "bw (frac. bandwidth):"
        lbl_bw.Left = 250
        lbl_bw.Top = 213
        labels.append(lbl_bw)

        edt_bw = vcl.TEdit(Form)
        edt_bw.Parent = Form
        edt_bw.Left = 380
        edt_bw.Top = 210
        edt_bw.Width = 70
        edt_bw.Text = "0.2"
        inputs["bw"] = edt_bw

        # bwr (reference level)
        lbl_bwr = vcl.TLabel(Form)
        lbl_bwr.Parent = Form
        lbl_bwr.Caption = "bwr (ref level) [dB]:"
        lbl_bwr.Left = 20
        lbl_bwr.Top = 243
        labels.append(lbl_bwr)

        edt_bwr = vcl.TEdit(Form)
        edt_bwr.Parent = Form
        edt_bwr.Left = 150
        edt_bwr.Top = 240
        edt_bwr.Width = 80
        edt_bwr.Text = "-6"
        inputs["bwr"] = edt_bwr

        # tpr (cutoff threshold)
        lbl_tpr = vcl.TLabel(Form)
        lbl_tpr.Parent = Form
        lbl_tpr.Caption = "tpr (threshold) [dB]:"
        lbl_tpr.Left = 250
        lbl_tpr.Top = 243
        labels.append(lbl_tpr)

        edt_tpr = vcl.TEdit(Form)
        edt_tpr.Parent = Form
        edt_tpr.Left = 380
        edt_tpr.Top = 240
        edt_tpr.Width = 70
        edt_tpr.Text = "-60"
        inputs["tpr"] = edt_tpr

        # =====================================================================
        # Output Options Section
        # =====================================================================
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 280
        sep3.Width = 450
        sep3.Height = 2
        sep3.Shape = "bsTopLine"

        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output Options"
        lbl_output.Left = 10
        lbl_output.Top = 290
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)

        # Checkboxes for optional outputs
        chk_yI = vcl.TCheckBox(Form)
        chk_yI.Parent = Form
        chk_yI.Caption = "yI (real part / in-phase)"
        chk_yI.Left = 20
        chk_yI.Top = 315
        chk_yI.Width = 200
        chk_yI.Checked = True
        chk_yI.Enabled = False  # Always enabled, always checked
        inputs["chk_yI"] = chk_yI

        chk_yQ = vcl.TCheckBox(Form)
        chk_yQ.Parent = Form
        chk_yQ.Caption = "yQ (imaginary part / quadrature)"
        chk_yQ.Left = 20
        chk_yQ.Top = 340
        chk_yQ.Width = 250
        chk_yQ.Checked = False
        inputs["chk_yQ"] = chk_yQ

        chk_yenv = vcl.TCheckBox(Form)
        chk_yenv.Parent = Form
        chk_yenv.Caption = "yenv (envelope)"
        chk_yenv.Left = 280
        chk_yenv.Top = 340
        chk_yenv.Width = 150
        chk_yenv.Checked = False
        inputs["chk_yenv"] = chk_yenv

        # =====================================================================
        # Appearance Section
        # =====================================================================
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10
        sep4.Top = 375
        sep4.Width = 450
        sep4.Height = 2
        sep4.Shape = "bsTopLine"

        lbl_appear = vcl.TLabel(Form)
        lbl_appear.Parent = Form
        lbl_appear.Caption = "Appearance"
        lbl_appear.Left = 10
        lbl_appear.Top = 385
        lbl_appear.Font.Style = {"fsBold"}
        labels.append(lbl_appear)

        # Line thickness
        lbl_thick = vcl.TLabel(Form)
        lbl_thick.Parent = Form
        lbl_thick.Caption = "Line Width:"
        lbl_thick.Left = 20
        lbl_thick.Top = 413
        labels.append(lbl_thick)

        edt_thick = vcl.TEdit(Form)
        edt_thick.Parent = Form
        edt_thick.Left = 100
        edt_thick.Top = 410
        edt_thick.Width = 50
        edt_thick.Text = "1"
        inputs["thick"] = edt_thick

        # =====================================================================
        # Buttons
        # =====================================================================
        sep5 = vcl.TBevel(Form)
        sep5.Parent = Form
        sep5.Left = 10
        sep5.Top = 445
        sep5.Width = 450
        sep5.Height = 2
        sep5.Shape = "bsTopLine"

        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Generate"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 140
        btn_ok.Top = 460
        btn_ok.Width = 100
        btn_ok.Height = 30

        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 250
        btn_cancel.Top = 460
        btn_cancel.Width = 100
        btn_cancel.Height = 30

        # Show dialog
        if Form.ShowModal() == 1:
            try:
                # Read parameters
                t0 = float(inputs["t0"].Text)
                tf = float(inputs["tf"].Text)
                fs = float(inputs["fs"].Text)
                fc = float(inputs["fc"].Text)
                bw = float(inputs["bw"].Text)
                bwr = float(inputs["bwr"].Text)
                tpr = float(inputs["tpr"].Text)
                thickness = int(inputs["thick"].Text)

                retquad = inputs["chk_yQ"].Checked
                retenv = inputs["chk_yenv"].Checked

                # Validate
                if fs <= 0:
                    raise ValueError("Sample rate must be > 0")
                if tf <= t0:
                    raise ValueError("End time must be > Start time")
                if fc <= 0:
                    raise ValueError("Center frequency must be > 0")
                if bw <= 0:
                    raise ValueError("Bandwidth must be > 0")

                # Generate time vector
                count = int((tf - t0) * fs) + 1
                t = np.linspace(t0, tf, count, endpoint=True)

                # Call gausspulse
                result = signal.gausspulse(t, fc=fc, bw=bw, bwr=bwr, tpr=tpr, 
                                           retquad=retquad, retenv=retenv)

                # Parse results based on options
                Point = namedtuple('Point', ['x', 'y'])
                
                # Determine what was returned
                if retquad and retenv:
                    yI, yQ, yenv = result
                elif retquad:
                    yI, yQ = result
                    yenv = None
                elif retenv:
                    yI, yenv = result
                    yQ = None
                else:
                    yI = result
                    yQ = None
                    yenv = None

                # Colors for different signals
                color_yI = 0x0000FF    # Red (BGR)
                color_yQ = 0x00AA00    # Green
                color_yenv = 0xFF8000  # Blue-ish

                # Create yI series (always)
                points_yI = [Point(t[i], yI[i]) for i in range(len(t))]
                series_yI = Graph.TPointSeries()
                series_yI.PointType = Graph.ptCartesian
                series_yI.Points = points_yI
                series_yI.LegendText = f"yI (fc={fc}Hz, bw={bw})"
                series_yI.Size = 0
                series_yI.Style = 0
                series_yI.FillColor = color_yI
                series_yI.FrameColor = color_yI
                series_yI.LineSize = thickness
                series_yI.LineColor = color_yI
                series_yI.ShowLabels = False
                Graph.FunctionList.append(series_yI)

                # Create yQ series (if requested)
                if yQ is not None:
                    points_yQ = [Point(t[i], yQ[i]) for i in range(len(t))]
                    series_yQ = Graph.TPointSeries()
                    series_yQ.PointType = Graph.ptCartesian
                    series_yQ.Points = points_yQ
                    series_yQ.LegendText = f"yQ (fc={fc}Hz, bw={bw})"
                    series_yQ.Size = 0
                    series_yQ.Style = 0
                    series_yQ.FillColor = color_yQ
                    series_yQ.FrameColor = color_yQ
                    series_yQ.LineSize = thickness
                    series_yQ.LineColor = color_yQ
                    series_yQ.ShowLabels = False
                    Graph.FunctionList.append(series_yQ)

                # Create yenv series (if requested)
                if yenv is not None:
                    points_yenv = [Point(t[i], yenv[i]) for i in range(len(t))]
                    series_yenv = Graph.TPointSeries()
                    series_yenv.PointType = Graph.ptCartesian
                    series_yenv.Points = points_yenv
                    series_yenv.LegendText = f"yenv (fc={fc}Hz, bw={bw})"
                    series_yenv.Size = 0
                    series_yenv.Style = 0
                    series_yenv.FillColor = color_yenv
                    series_yenv.FrameColor = color_yenv
                    series_yenv.LineSize = thickness
                    series_yenv.LineColor = color_yenv
                    # Use dashed line for envelope
                    series_yenv.LineStyle = 1
                    series_yenv.ShowLabels = False
                    Graph.FunctionList.append(series_yenv)

                Graph.Update()

            except Exception as e:
                vcl.MessageDlg(f"Parameter error: {str(e)}", 1, [0], 0)

    finally:
        Form.Free()


# Create action for custom menu
GaussPulseAction = Graph.CreateAction(
    Caption="Gauss Pulse...",
    OnExecute=GaussPulseDialog,
    Hint="Generate Gaussian modulated sinusoid pulse (scipy.signal.gausspulse)",
    ShortCut="",
    IconFile=os.path.join(os.path.dirname(__file__), "GaussPulse_sm.png")
)

# Add action to 'AWF Generators' submenu under 'Plugins -> Graphîa'
Graph.AddActionToMainMenu(GaussPulseAction, TopMenu="Plugins", SubMenus=["Graphîa", "AWF Generators"])  # type: ignore
