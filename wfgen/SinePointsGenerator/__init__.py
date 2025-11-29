# Plugin to generate a series of points from a composite sinusoidal signal
import sys
import os

# Add virtual environment to path to find numpy
venv_site_packages = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".venv", "Lib", "site-packages")
if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
    sys.path.append(venv_site_packages)

import Graph
import math
import vcl
import numpy as np

PluginName = "Sine Points Generator"
PluginVersion = "1.3"
PluginDescription = "Generates a composite signal from the sum of 6 sinusoidals."

def GenerateSinePoints(Action):
    # Create input form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Composite Signal Generator"
        Form.Width = 480
        Form.Height = 580
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"

        inputs = {}
        labels = []  # Keep references to prevent GC

        # Help panel at top
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
        lbl_help_title.Caption = "Composite Signal Generator"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        lbl_help = vcl.TLabel(help_panel)
        lbl_help.Parent = help_panel
        lbl_help.Caption = "Generates: Σ [Aₙ·sin(2πfₙt+φₙ) + Cₙ] + noise  (n=1..6)"
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)

        # Separator after help
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 75
        sep1.Width = 450
        sep1.Height = 2
        sep1.Shape = "bsTopLine"

        # Signal components section title
        lbl_signals = vcl.TLabel(Form)
        lbl_signals.Parent = Form
        lbl_signals.Caption = "Signal Components"
        lbl_signals.Left = 10
        lbl_signals.Top = 85
        lbl_signals.Font.Style = {"fsBold"}
        labels.append(lbl_signals)

        # Column headers
        lbl_hdr_a = vcl.TLabel(Form, Parent=Form, Caption="Ampl [V]", Left=90, Top=105)
        lbl_hdr_a.Font.Color = 0x666666
        labels.append(lbl_hdr_a)
        lbl_hdr_f = vcl.TLabel(Form, Parent=Form, Caption="Freq [Hz]", Left=170, Top=105)
        lbl_hdr_f.Font.Color = 0x666666
        labels.append(lbl_hdr_f)
        lbl_hdr_p = vcl.TLabel(Form, Parent=Form, Caption="Phase [rad]", Left=250, Top=105)
        lbl_hdr_p.Font.Color = 0x666666
        labels.append(lbl_hdr_p)
        lbl_hdr_o = vcl.TLabel(Form, Parent=Form, Caption="Offset [V]", Left=340, Top=105)
        lbl_hdr_o.Font.Color = 0x666666
        labels.append(lbl_hdr_o)

        # Function to create signal rows
        def create_signal_row(parent, y, title, prefix, def_a, def_f, def_p, def_o):
            lbl = vcl.TLabel(parent)
            lbl.Parent = parent
            lbl.Caption = title
            lbl.Left = 20
            lbl.Top = y + 3
            labels.append(lbl)

            ea = vcl.TEdit(parent, Parent=parent, Left=90, Top=y, Width=60, Text=str(def_a))
            inputs[f"{prefix}_a"] = ea

            ef = vcl.TEdit(parent, Parent=parent, Left=170, Top=y, Width=60, Text=str(def_f))
            inputs[f"{prefix}_f"] = ef

            ep = vcl.TEdit(parent, Parent=parent, Left=250, Top=y, Width=60, Text=str(def_p))
            inputs[f"{prefix}_p"] = ep

            eo = vcl.TEdit(parent, Parent=parent, Left=340, Top=y, Width=60, Text=str(def_o))
            inputs[f"{prefix}_o"] = eo

        # Create 6 signal rows
        create_signal_row(Form, 125, "Signal 1:", "s1", 4/np.pi, 1.0, 0.0, 0.0)
        create_signal_row(Form, 150, "Signal 2:", "s2", 4/(3*np.pi), 3.0, 0.0, 0.0)
        create_signal_row(Form, 175, "Signal 3:", "s3", 0, 5.0, 0.0, 0.0)
        create_signal_row(Form, 200, "Signal 4:", "s4", 0, 7.0, 0.0, 0.0)
        create_signal_row(Form, 225, "Signal 5:", "s5", 0, 9.0, 0.0, 0.0)
        create_signal_row(Form, 250, "Signal 6:", "s6", 0, 11.0, 0.0, 0.0)

        # Separator
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 285
        sep2.Width = 450
        sep2.Height = 2
        sep2.Shape = "bsTopLine"

        # Sampling parameters section
        lbl_samp = vcl.TLabel(Form)
        lbl_samp.Parent = Form
        lbl_samp.Caption = "Sampling Parameters"
        lbl_samp.Left = 10
        lbl_samp.Top = 295
        lbl_samp.Font.Style = {"fsBold"}
        labels.append(lbl_samp)

        # Sampling frequency
        l_fs = vcl.TLabel(Form, Parent=Form, Caption="Sample Rate [Hz]:", Left=20, Top=323)
        labels.append(l_fs)
        inputs["fs"] = vcl.TEdit(Form, Parent=Form, Left=130, Top=320, Width=80, Text="1000")

        # Time range
        l_ts = vcl.TLabel(Form, Parent=Form, Caption="Start Time [s]:", Left=20, Top=353)
        labels.append(l_ts)
        inputs["ts"] = vcl.TEdit(Form, Parent=Form, Left=130, Top=350, Width=80, Text="0")

        l_te = vcl.TLabel(Form, Parent=Form, Caption="End Time [s]:", Left=240, Top=353)
        labels.append(l_te)
        inputs["te"] = vcl.TEdit(Form, Parent=Form, Left=330, Top=350, Width=80, Text="2.000")

        # Noise
        l_noise = vcl.TLabel(Form, Parent=Form, Caption="Noise [std dev]:", Left=20, Top=383)
        labels.append(l_noise)
        inputs["noise"] = vcl.TEdit(Form, Parent=Form, Left=130, Top=380, Width=80, Text="0")

        # Separator
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 415
        sep3.Width = 450
        sep3.Height = 2
        sep3.Shape = "bsTopLine"

        # Appearance section
        lbl_appear = vcl.TLabel(Form)
        lbl_appear.Parent = Form
        lbl_appear.Caption = "Appearance"
        lbl_appear.Left = 10
        lbl_appear.Top = 425
        lbl_appear.Font.Style = {"fsBold"}
        labels.append(lbl_appear)

        # Color
        l_color = vcl.TLabel(Form, Parent=Form, Caption="Line Color:", Left=20, Top=453)
        labels.append(l_color)

        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 100
        cb_color.Top = 450
        cb_color.Width = 110
        cb_color.Selected = 0x000000  # Black
        inputs["color_box"] = cb_color

        # Thickness
        l_thick = vcl.TLabel(Form, Parent=Form, Caption="Line Width:", Left=240, Top=453)
        labels.append(l_thick)
        inputs["thick"] = vcl.TEdit(Form, Parent=Form, Left=320, Top=450, Width=50, Text="1")

        # Separator before buttons
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10
        sep4.Top = 490
        sep4.Width = 450
        sep4.Height = 2
        sep4.Shape = "bsTopLine"

        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Generate"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 140
        btn_ok.Top = 505
        btn_ok.Width = 100
        btn_ok.Height = 30

        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 250
        btn_cancel.Top = 505
        btn_cancel.Width = 100
        btn_cancel.Height = 30

        # Show dialog
        if Form.ShowModal() == 1:
            try:
                # Read signal values (6 signals with amplitude, frequency, phase, offset)
                signals = []
                for i in range(1, 7):
                    prefix = f"s{i}"
                    sig = {
                        'a': float(inputs[f"{prefix}_a"].Text),
                        'f': float(inputs[f"{prefix}_f"].Text),
                        'p': float(inputs[f"{prefix}_p"].Text),
                        'o': float(inputs[f"{prefix}_o"].Text)
                    }
                    signals.append(sig)

                fs = float(inputs["fs"].Text)
                ts = float(inputs["ts"].Text)
                te = float(inputs["te"].Text)
                
                # Get noise amplitude (can be a number or custom constant)
                noise_text = inputs["noise"].Text.strip()
                try:
                    noise_amp = float(noise_text)
                except ValueError:
                    # Try to evaluate as Graph custom constant
                    try:
                        noise_amp = float(Graph.Eval(noise_text))
                    except:
                        raise ValueError(f"'{noise_text}' is not a valid number or defined constant")
                
                # Convert color to int to avoid errors with special colors
                color_val = int(inputs["color_box"].Selected) & 0xFFFFFF
                
                thickness = int(inputs["thick"].Text)

                if fs <= 0: raise ValueError("Sample rate must be > 0")
                if te <= ts: raise ValueError("End time must be > Start time")

                # Generate points
                from collections import namedtuple
                Point = namedtuple('Point', ['x', 'y'])
                points = []
                
                count = int((te - ts) * fs) + 1
                noise = noise_amp * np.random.randn(count)

                for i in range(count):
                    t = ts + i / fs
                    y = sum(
                        sig['a'] * math.sin(2 * math.pi * sig['f'] * t + sig['p']) + sig['o']
                        for sig in signals
                    ) + noise[i]
                    points.append(Point(t, y))

                # Build legend
                legend_parts = []
                for idx, sig in enumerate(signals, 1):
                    a, f, p, o = sig['a'], sig['f'], sig['p'], sig['o']
                    if a != 0 or o != 0:
                        term = ""
                        if a != 0:
                            term = f"{a}·sin(2π·{f}·t"
                            if p != 0:
                                term += f"+{p}"
                            term += ")"
                        if o != 0:
                            if term:
                                term += f"+{o}" if o > 0 else f"{o}"
                            else:
                                term = str(o)
                        if term:
                            legend_parts.append(term)
                
                if noise_amp > 0:
                    legend_parts.append(f"noise({noise_amp})")
                
                legend_text = " + ".join(legend_parts) if legend_parts else "0"

                # Create series
                point_series = Graph.TPointSeries()
                point_series.PointType = Graph.ptCartesian
                point_series.Points = points
                point_series.LegendText = legend_text
                point_series.Size = 0
                point_series.Style = 0  # Circle
                point_series.FillColor = color_val
                point_series.FrameColor = color_val
                point_series.LineSize = thickness
                point_series.LineColor = color_val
                point_series.ShowLabels = False

                Graph.FunctionList.append(point_series)
                Graph.Update()

            except Exception as e:
                vcl.MessageDlg(f"Parameter error: {str(e)}", 1, [0], 0)

    finally:
        Form.Free()


# Create action for custom menu
SinePointsAction = Graph.CreateAction(
    Caption="Sine Points Generator",
    OnExecute=GenerateSinePoints,
    Hint="Generates a composite sinusoidal signal.",
    ShortCut="Ctrl+P",
    IconFile=os.path.join(os.path.dirname(__file__), "SineWave_sm.png")
)

# Add action to 'Signal Processing' submenu under 'Plugins'
Graph.AddActionToMainMenu(SinePointsAction, TopMenu="Plugins", SubMenus=["Graphîa", "AWF Generators"])  # type: ignore
