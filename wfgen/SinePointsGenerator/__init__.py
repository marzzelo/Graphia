# Plugin to generate a series of points from a composite sinusoidal signal or arbitrary functions
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
import re

PluginName = "Sine Points Generator"
PluginVersion = "1.6"
PluginDescription = "Generates composite signals from sinusoidals or arbitrary functions."

def GenerateSinePoints(Action):
    # Create input form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Composite Signal Generator"
        Form.Width = 520
        Form.Height = 700
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"

        inputs = {}
        labels = []  # Keep references to prevent GC
        sin_controls = []  # Controls for sinusoidal mode
        arb_controls = []  # Controls for arbitrary mode

        # Help panel at top
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 10
        help_panel.Top = 10
        help_panel.Width = 490
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
        lbl_help.Caption = "Generates: Σ Aₙ·sin(2πfₙt+φₙ) + C + noise  (n=1..6)"
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)

        # Separator after help
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 75
        sep1.Width = 490
        sep1.Height = 2
        sep1.Shape = "bsTopLine"

        # Function type selection
        lbl_func_type = vcl.TLabel(Form)
        lbl_func_type.Parent = Form
        lbl_func_type.Caption = "Function Type:"
        lbl_func_type.Left = 10
        lbl_func_type.Top = 85
        lbl_func_type.Font.Style = {"fsBold"}
        labels.append(lbl_func_type)

        rb_sinusoidal = vcl.TRadioButton(Form)
        rb_sinusoidal.Parent = Form
        rb_sinusoidal.Caption = "Sinusoidal"
        rb_sinusoidal.Left = 120
        rb_sinusoidal.Top = 85
        rb_sinusoidal.Width = 120
        rb_sinusoidal.Checked = True

        rb_arbitrary = vcl.TRadioButton(Form)
        rb_arbitrary.Parent = Form
        rb_arbitrary.Caption = "Arbitrary"
        rb_arbitrary.Left = 260
        rb_arbitrary.Top = 85
        rb_arbitrary.Width = 180

        # Separator
        sep1b = vcl.TBevel(Form)
        sep1b.Parent = Form
        sep1b.Left = 10
        sep1b.Top = 110
        sep1b.Width = 490
        sep1b.Height = 2
        sep1b.Shape = "bsTopLine"

        # Signal components section title
        lbl_signals = vcl.TLabel(Form)
        lbl_signals.Parent = Form
        lbl_signals.Caption = "Signal Components"
        lbl_signals.Left = 10
        lbl_signals.Top = 120
        lbl_signals.Font.Style = {"fsBold"}
        labels.append(lbl_signals)

        # =========================================================================
        # Sinusoidal mode controls
        # =========================================================================
        
        # Column headers for sinusoidal
        lbl_hdr_a = vcl.TLabel(Form, Parent=Form, Caption="Ampl [V]", Left=90, Top=140)
        lbl_hdr_a.Font.Color = 0x666666
        labels.append(lbl_hdr_a)
        sin_controls.append(lbl_hdr_a)
        
        lbl_hdr_f = vcl.TLabel(Form, Parent=Form, Caption="Freq [Hz]", Left=200, Top=140)
        lbl_hdr_f.Font.Color = 0x666666
        labels.append(lbl_hdr_f)
        sin_controls.append(lbl_hdr_f)
        
        lbl_hdr_p = vcl.TLabel(Form, Parent=Form, Caption="Phase [rad]", Left=310, Top=140)
        lbl_hdr_p.Font.Color = 0x666666
        labels.append(lbl_hdr_p)
        sin_controls.append(lbl_hdr_p)

        # Default values for sinusoidal
        sin_defaults = [
            (4/np.pi, 1.0, 0.0),
            (4/(3*np.pi), 3.0, 0.0),
            (0, 5.0, 0.0),
            (0, 7.0, 0.0),
            (0, 9.0, 0.0),
            (0, 11.0, 0.0)
        ]

        # Function to create sinusoidal signal rows
        def create_sin_row(parent, y, title, prefix, def_a, def_f, def_p):
            lbl = vcl.TLabel(parent)
            lbl.Parent = parent
            lbl.Caption = title
            lbl.Left = 20
            lbl.Top = y + 3
            labels.append(lbl)
            sin_controls.append(lbl)

            ea = vcl.TEdit(parent, Parent=parent, Left=90, Top=y, Width=90, Text=str(def_a))
            inputs[f"{prefix}_a"] = ea
            sin_controls.append(ea)

            ef = vcl.TEdit(parent, Parent=parent, Left=200, Top=y, Width=90, Text=str(def_f))
            inputs[f"{prefix}_f"] = ef
            sin_controls.append(ef)

            ep = vcl.TEdit(parent, Parent=parent, Left=310, Top=y, Width=90, Text=str(def_p))
            inputs[f"{prefix}_p"] = ep
            sin_controls.append(ep)

        # Create 6 sinusoidal signal rows
        create_sin_row(Form, 160, "Signal 1:", "s1", *sin_defaults[0])
        create_sin_row(Form, 185, "Signal 2:", "s2", *sin_defaults[1])
        create_sin_row(Form, 210, "Signal 3:", "s3", *sin_defaults[2])
        create_sin_row(Form, 235, "Signal 4:", "s4", *sin_defaults[3])
        create_sin_row(Form, 260, "Signal 5:", "s5", *sin_defaults[4])
        create_sin_row(Form, 285, "Signal 6:", "s6", *sin_defaults[5])

        # =========================================================================
        # Arbitrary mode controls
        # =========================================================================
        
        # Column header for arbitrary
        lbl_hdr_formula = vcl.TLabel(Form, Parent=Form, Caption="Formula f(x)  -  Use 'x' as the variable", Left=90, Top=140)
        lbl_hdr_formula.Font.Color = 0x666666
        lbl_hdr_formula.Width = 350
        lbl_hdr_formula.Visible = False
        labels.append(lbl_hdr_formula)
        arb_controls.append(lbl_hdr_formula)

        # Default formulas for arbitrary mode
        arb_defaults = ["sin(x)", "", "", "", "", ""]

        # Function to create arbitrary signal rows
        def create_arb_row(parent, y, title, prefix, def_formula):
            lbl = vcl.TLabel(parent)
            lbl.Parent = parent
            lbl.Caption = title
            lbl.Left = 20
            lbl.Top = y + 3
            lbl.Visible = False
            labels.append(lbl)
            arb_controls.append(lbl)

            ef = vcl.TEdit(parent, Parent=parent, Left=90, Top=y, Width=380, Text=def_formula)
            ef.Visible = False
            inputs[f"{prefix}_formula"] = ef
            arb_controls.append(ef)

        # Create 6 arbitrary formula rows
        create_arb_row(Form, 160, "Formula 1:", "f1", arb_defaults[0])
        create_arb_row(Form, 185, "Formula 2:", "f2", arb_defaults[1])
        create_arb_row(Form, 210, "Formula 3:", "f3", arb_defaults[2])
        create_arb_row(Form, 235, "Formula 4:", "f4", arb_defaults[3])
        create_arb_row(Form, 260, "Formula 5:", "f5", arb_defaults[4])
        create_arb_row(Form, 285, "Formula 6:", "f6", arb_defaults[5])

        # Function to toggle between sinusoidal and arbitrary modes
        def on_function_type_change(Sender):
            is_sin = rb_sinusoidal.Checked
            for ctrl in sin_controls:
                ctrl.Visible = is_sin
            for ctrl in arb_controls:
                ctrl.Visible = not is_sin
            if is_sin:
                lbl_help.Caption = "Generates: Σ Aₙ·sin(2πfₙt+φₙ) + C + noise  (n=1..6)"
            else:
                lbl_help.Caption = "Generates: Σ fₙ(x) + C + noise  (n=1..6)"

        rb_sinusoidal.OnClick = on_function_type_change
        rb_arbitrary.OnClick = on_function_type_change

        # Separator
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 320
        sep2.Width = 490
        sep2.Height = 2
        sep2.Shape = "bsTopLine"

        # Sampling parameters section
        lbl_samp = vcl.TLabel(Form)
        lbl_samp.Parent = Form
        lbl_samp.Caption = "Sampling Parameters"
        lbl_samp.Left = 10
        lbl_samp.Top = 330
        lbl_samp.Font.Style = {"fsBold"}
        labels.append(lbl_samp)

        # Sampling frequency
        l_fs = vcl.TLabel(Form, Parent=Form, Caption="Sample Rate [Hz]:", Left=20, Top=358)
        labels.append(l_fs)
        inputs["fs"] = vcl.TEdit(Form, Parent=Form, Left=130, Top=355, Width=80, Text="1000")

        # General offset
        l_offset = vcl.TLabel(Form, Parent=Form, Caption="Offset [V]:", Left=250, Top=358)
        labels.append(l_offset)
        inputs["offset"] = vcl.TEdit(Form, Parent=Form, Left=330, Top=355, Width=80, Text="0")

        # Time range
        l_ts = vcl.TLabel(Form, Parent=Form, Caption="Start Time [s]:", Left=20, Top=388)
        labels.append(l_ts)
        inputs["ts"] = vcl.TEdit(Form, Parent=Form, Left=130, Top=385, Width=80, Text="0")

        l_te = vcl.TLabel(Form, Parent=Form, Caption="End Time [s]:", Left=240, Top=388)
        labels.append(l_te)
        inputs["te"] = vcl.TEdit(Form, Parent=Form, Left=330, Top=385, Width=80, Text="2.000")

        # Noise
        l_noise = vcl.TLabel(Form, Parent=Form, Caption="Noise [std dev]:", Left=20, Top=418)
        labels.append(l_noise)
        inputs["noise"] = vcl.TEdit(Form, Parent=Form, Left=130, Top=415, Width=80, Text="0")

        # Separator
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 450
        sep3.Width = 490
        sep3.Height = 2
        sep3.Shape = "bsTopLine"

        # Output options section
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output Options"
        lbl_output.Left = 10
        lbl_output.Top = 460
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)

        # Compose checkbox
        chk_compose = vcl.TCheckBox(Form)
        chk_compose.Parent = Form
        chk_compose.Caption = "Compose (sum all signals into one series)"
        chk_compose.Left = 20
        chk_compose.Top = 485
        chk_compose.Width = 300
        chk_compose.Checked = True

        # Separator
        sep3b = vcl.TBevel(Form)
        sep3b.Parent = Form
        sep3b.Left = 10
        sep3b.Top = 515
        sep3b.Width = 490
        sep3b.Height = 2
        sep3b.Shape = "bsTopLine"

        # Appearance section
        lbl_appear = vcl.TLabel(Form)
        lbl_appear.Parent = Form
        lbl_appear.Caption = "Appearance"
        lbl_appear.Left = 10
        lbl_appear.Top = 525
        lbl_appear.Font.Style = {"fsBold"}
        labels.append(lbl_appear)

        # Color
        l_color = vcl.TLabel(Form, Parent=Form, Caption="Line Color:", Left=20, Top=553)
        labels.append(l_color)

        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 100
        cb_color.Top = 550
        cb_color.Width = 110
        cb_color.Selected = 0x000000  # Black
        inputs["color_box"] = cb_color

        # Thickness
        l_thick = vcl.TLabel(Form, Parent=Form, Caption="Line Width:", Left=240, Top=553)
        labels.append(l_thick)
        inputs["thick"] = vcl.TEdit(Form, Parent=Form, Left=320, Top=550, Width=50, Text="1")

        # Separator before buttons
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10
        sep4.Top = 590
        sep4.Width = 490
        sep4.Height = 2
        sep4.Shape = "bsTopLine"

        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Generate"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 160
        btn_ok.Top = 610
        btn_ok.Width = 100
        btn_ok.Height = 30

        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 270
        btn_cancel.Top = 610
        btn_cancel.Width = 100
        btn_cancel.Height = 30

        # Show dialog
        if Form.ShowModal() == 1:
            try:
                # Determine function type and compose mode
                is_sinusoidal = rb_sinusoidal.Checked
                compose = chk_compose.Checked

                fs = float(inputs["fs"].Text)
                offset = float(inputs["offset"].Text)
                ts = float(inputs["ts"].Text)
                te = float(inputs["te"].Text)
                
                # Get noise amplitude (can be a number or custom constant)
                noise_text = inputs["noise"].Text.strip()
                try:
                    noise_amp = float(noise_text)
                except ValueError:
                    try:
                        noise_amp = float(Graph.Eval(noise_text))
                    except:
                        raise ValueError(f"'{noise_text}' is not a valid number or defined constant")
                
                # Convert color to int to avoid errors with special colors
                color_val = int(inputs["color_box"].Selected) & 0xFFFFFF
                thickness = int(inputs["thick"].Text)

                if fs <= 0: raise ValueError("Sample rate must be > 0")
                if te <= ts: raise ValueError("End time must be > Start time")

                from collections import namedtuple
                Point = namedtuple('Point', ['x', 'y'])
                
                count = int((te - ts) * fs) + 1
                noise = noise_amp * np.random.randn(count)
                
                # Different colors for separate series
                colors = [0x0000FF, 0x00FF00, 0xFF0000, 0xFF00FF, 0x00FFFF, 0xFFFF00]

                if is_sinusoidal:
                    # Read sinusoidal signal values
                    signals = []
                    for i in range(1, 7):
                        prefix = f"s{i}"
                        sig = {
                            'a': float(inputs[f"{prefix}_a"].Text),
                            'f': float(inputs[f"{prefix}_f"].Text),
                            'p': float(inputs[f"{prefix}_p"].Text)
                        }
                        signals.append(sig)
                    
                    if compose:
                        # Generate composed signal
                        points = []
                        for i in range(count):
                            t = ts + i / fs
                            y = sum(
                                sig['a'] * math.sin(2 * math.pi * sig['f'] * t + sig['p'])
                                for sig in signals
                            ) + offset + noise[i]
                            points.append(Point(t, y))
                        
                        # Build legend
                        legend_parts = []
                        for sig in signals:
                            a, f, p = sig['a'], sig['f'], sig['p']
                            if a != 0:
                                term = f"{a:.4g}·sin(2π·{f}·t"
                                if p != 0:
                                    term += f"+{p}"
                                term += ")"
                                legend_parts.append(term)
                        if offset != 0:
                            legend_parts.append(str(offset))
                        if noise_amp > 0:
                            legend_parts.append(f"noise({noise_amp})")
                        legend_text = " + ".join(legend_parts) if legend_parts else "0"
                        
                        # Create series
                        point_series = Graph.TPointSeries()
                        point_series.PointType = Graph.ptCartesian
                        point_series.Points = points
                        point_series.LegendText = legend_text
                        point_series.Size = 0
                        point_series.Style = 0
                        point_series.FillColor = color_val
                        point_series.FrameColor = color_val
                        point_series.LineSize = thickness
                        point_series.LineColor = color_val
                        point_series.ShowLabels = False
                        Graph.FunctionList.append(point_series)
                    else:
                        # Generate separate series for each signal
                        for idx, sig in enumerate(signals):
                            a, f, p = sig['a'], sig['f'], sig['p']
                            if a == 0:
                                continue
                            
                            points = []
                            sig_noise = noise if idx == 0 else np.zeros(count)
                            sig_offset = offset if idx == 0 else 0
                            
                            for i in range(count):
                                t = ts + i / fs
                                y = a * math.sin(2 * math.pi * f * t + p) + sig_offset + sig_noise[i]
                                points.append(Point(t, y))
                            
                            legend = f"{a:.4g}·sin(2π·{f}·t"
                            if p != 0:
                                legend += f"+{p}"
                            legend += ")"
                            
                            point_series = Graph.TPointSeries()
                            point_series.PointType = Graph.ptCartesian
                            point_series.Points = points
                            point_series.LegendText = legend
                            point_series.Size = 0
                            point_series.Style = 0
                            series_color = colors[idx % len(colors)]
                            point_series.FillColor = series_color
                            point_series.FrameColor = series_color
                            point_series.LineSize = thickness
                            point_series.LineColor = series_color
                            point_series.ShowLabels = False
                            Graph.FunctionList.append(point_series)
                
                else:
                    # Arbitrary mode
                    formulas = []
                    for i in range(1, 7):
                        formula = inputs[f"f{i}_formula"].Text.strip()
                        formulas.append(formula)
                    
                    if compose:
                        # Generate composed signal from all formulas
                        points = []
                        for i in range(count):
                            t = ts + i / fs
                            y_total = 0
                            for formula in formulas:
                                if formula:
                                    # Replace 'x' with the time value
                                    expr = re.sub(r'\bx\b', f'({t})', formula)
                                    try:
                                        y_val = float(Graph.Eval(expr))
                                        y_total += y_val
                                    except:
                                        pass
                            y_total += offset + noise[i]
                            points.append(Point(t, y_total))
                        
                        # Build legend
                        legend_parts = [f for f in formulas if f]
                        if offset != 0:
                            legend_parts.append(str(offset))
                        if noise_amp > 0:
                            legend_parts.append(f"noise({noise_amp})")
                        legend_text = " + ".join(legend_parts) if legend_parts else "0"
                        
                        point_series = Graph.TPointSeries()
                        point_series.PointType = Graph.ptCartesian
                        point_series.Points = points
                        point_series.LegendText = legend_text
                        point_series.Size = 0
                        point_series.Style = 0
                        point_series.FillColor = color_val
                        point_series.FrameColor = color_val
                        point_series.LineSize = thickness
                        point_series.LineColor = color_val
                        point_series.ShowLabels = False
                        Graph.FunctionList.append(point_series)
                    else:
                        # Generate separate series for each formula
                        for idx, formula in enumerate(formulas):
                            if not formula:
                                continue
                            
                            points = []
                            sig_noise = noise if idx == 0 else np.zeros(count)
                            sig_offset = offset if idx == 0 else 0
                            
                            for i in range(count):
                                t = ts + i / fs
                                expr = re.sub(r'\bx\b', f'({t})', formula)
                                try:
                                    y = float(Graph.Eval(expr)) + sig_offset + sig_noise[i]
                                except:
                                    y = 0
                                points.append(Point(t, y))
                            
                            point_series = Graph.TPointSeries()
                            point_series.PointType = Graph.ptCartesian
                            point_series.Points = points
                            point_series.LegendText = formula
                            point_series.Size = 0
                            point_series.Style = 0
                            series_color = colors[idx % len(colors)]
                            point_series.FillColor = series_color
                            point_series.FrameColor = series_color
                            point_series.LineSize = thickness
                            point_series.LineColor = series_color
                            point_series.ShowLabels = False
                            Graph.FunctionList.append(point_series)

                Graph.Update()

            except Exception as e:
                vcl.MessageDlg(f"Parameter error: {str(e)}", 1, [0], 0)

    finally:
        Form.Free()


# Create action for custom menu
SinePointsAction = Graph.CreateAction(
    Caption="Signal Generator",
    OnExecute=GenerateSinePoints,
    Hint="Generates composite sinusoidal or arbitrary signals.",
    ShortCut="Ctrl+P",
    IconFile=os.path.join(os.path.dirname(__file__), "SineWave_sm.png")
)

# Add action to 'Signal Processing' submenu under 'Plugins'
Graph.AddActionToMainMenu(SinePointsAction, TopMenu="Plugins", SubMenus=["Graphîa", "AWF Generators"])  # type: ignore
