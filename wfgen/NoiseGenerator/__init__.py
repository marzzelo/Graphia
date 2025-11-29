# Plugin to add noise to a selected point series
import os

# Import common module (automatically configures venv)
from common import (
    get_selected_point_series, show_error, safe_color,
    get_series_stats, Point, Graph, vcl
)

import numpy as np

PluginName = "Noise Generator"
PluginVersion = "1.0"
PluginDescription = "Adds random noise to the selected point series."


def add_noise(Action):
    """Adds random noise to the selected point series."""
    
    # Check that a TPointSeries is selected
    point_series, error_msg = get_selected_point_series()
    
    if point_series is None:
        show_error(error_msg, "Noise Generator")
        return
    
    # Verify the series has points
    points = point_series.Points
    if not points or len(points) < 2:
        show_error(
            "The point series must have at least 2 points.",
            "Noise Generator"
        )
        return
    
    # Get series statistics
    stats = get_series_stats(point_series)
    n_points = stats['n_points']
    y_min, y_max = stats['y_min'], stats['y_max']
    y_range = stats['y_range']
    
    # Create configuration form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Noise Generator"
        Form.Width = 420
        Form.Height = 510
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        labels = []  # Keep references
        
        # Help panel at top
        help_panel = vcl.TPanel(Form)
        help_panel.Parent = Form
        help_panel.Left = 10
        help_panel.Top = 10
        help_panel.Width = 390
        help_panel.Height = 55
        help_panel.BevelOuter = "bvLowered"
        help_panel.Color = 0xFFF8F0

        lbl_help_title = vcl.TLabel(help_panel)
        lbl_help_title.Parent = help_panel
        lbl_help_title.Caption = "Noise Generator"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        lbl_help = vcl.TLabel(help_panel)
        lbl_help.Parent = help_panel
        lbl_help.Caption = f"Selected series: {n_points} points  |  Y range: [{y_min:.4g}, {y_max:.4g}]"
        lbl_help.Left = 10
        lbl_help.Top = 28
        lbl_help.Font.Color = 0x804000
        labels.append(lbl_help)

        # Separator
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 75
        sep1.Width = 390
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Noise type section
        lbl_type = vcl.TLabel(Form)
        lbl_type.Parent = Form
        lbl_type.Caption = "Noise Type"
        lbl_type.Left = 10
        lbl_type.Top = 85
        lbl_type.Font.Style = {"fsBold"}
        labels.append(lbl_type)
        
        # Panel to group noise type radio buttons
        pnl_noise_type = vcl.TPanel(Form)
        pnl_noise_type.Parent = Form
        pnl_noise_type.Left = 10
        pnl_noise_type.Top = 105
        pnl_noise_type.Width = 300
        pnl_noise_type.Height = 55
        pnl_noise_type.BevelOuter = "bvNone"
        
        # Radio buttons for noise type
        rb_normal = vcl.TRadioButton(Form)
        rb_normal.Parent = pnl_noise_type
        rb_normal.Caption = "Normal Distribution (Gaussian)"
        rb_normal.Left = 10
        rb_normal.Top = 5
        rb_normal.Width = 250
        rb_normal.Checked = True
        
        rb_uniform = vcl.TRadioButton(Form)
        rb_uniform.Parent = pnl_noise_type
        rb_uniform.Caption = "Uniform Distribution"
        rb_uniform.Left = 10
        rb_uniform.Top = 30
        rb_uniform.Width = 250
        
        # Separator
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 165
        sep2.Width = 390
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        # Parameters section
        lbl_params = vcl.TLabel(Form)
        lbl_params.Parent = Form
        lbl_params.Caption = "Parameters"
        lbl_params.Left = 10
        lbl_params.Top = 175
        lbl_params.Font.Style = {"fsBold"}
        labels.append(lbl_params)
        
        # Normal distribution parameters
        lbl_loc = vcl.TLabel(Form)
        lbl_loc.Parent = Form
        lbl_loc.Caption = "Central Value (loc):"
        lbl_loc.Left = 20
        lbl_loc.Top = 203
        labels.append(lbl_loc)
        
        edit_loc = vcl.TEdit(Form)
        edit_loc.Parent = Form
        edit_loc.Left = 160
        edit_loc.Top = 200
        edit_loc.Width = 80
        edit_loc.Text = "0"
        
        lbl_scale = vcl.TLabel(Form)
        lbl_scale.Parent = Form
        lbl_scale.Caption = "Std. Dev (scale):"
        lbl_scale.Left = 20
        lbl_scale.Top = 233
        labels.append(lbl_scale)
        
        edit_scale = vcl.TEdit(Form)
        edit_scale.Parent = Form
        edit_scale.Left = 160
        edit_scale.Top = 230
        edit_scale.Width = 80
        edit_scale.Text = "1"
        
        # Uniform distribution parameters
        lbl_low = vcl.TLabel(Form)
        lbl_low.Parent = Form
        lbl_low.Caption = "Lower Limit (low):"
        lbl_low.Left = 20
        lbl_low.Top = 203
        lbl_low.Visible = False
        labels.append(lbl_low)
        
        edit_low = vcl.TEdit(Form)
        edit_low.Parent = Form
        edit_low.Left = 160
        edit_low.Top = 200
        edit_low.Width = 80
        edit_low.Text = "-1"
        edit_low.Visible = False
        
        lbl_high = vcl.TLabel(Form)
        lbl_high.Parent = Form
        lbl_high.Caption = "Upper Limit (high):"
        lbl_high.Left = 20
        lbl_high.Top = 233
        lbl_high.Visible = False
        labels.append(lbl_high)
        
        edit_high = vcl.TEdit(Form)
        edit_high.Parent = Form
        edit_high.Left = 160
        edit_high.Top = 230
        edit_high.Width = 80
        edit_high.Text = "1"
        edit_high.Visible = False
        
        # Help panel for distribution info
        info_panel = vcl.TPanel(Form)
        info_panel.Parent = Form
        info_panel.Left = 20
        info_panel.Top = 270
        info_panel.Width = 370
        info_panel.Height = 50
        info_panel.BevelOuter = "bvLowered"
        info_panel.Color = 0xF0FFF0
        
        lbl_info = vcl.TLabel(info_panel)
        lbl_info.Parent = info_panel
        lbl_info.Caption = "Normal: Generates random numbers with normal (Gaussian)\ndistribution centered at 'loc' with standard deviation 'scale'."
        lbl_info.Left = 10
        lbl_info.Top = 10
        lbl_info.Font.Color = 0x006400
        labels.append(lbl_info)
        
        # Function to switch visibility based on selection
        def on_type_change(Sender):
            is_normal = rb_normal.Checked
            # Normal params
            lbl_loc.Visible = is_normal
            edit_loc.Visible = is_normal
            lbl_scale.Visible = is_normal
            edit_scale.Visible = is_normal
            # Uniform params
            lbl_low.Visible = not is_normal
            edit_low.Visible = not is_normal
            lbl_high.Visible = not is_normal
            edit_high.Visible = not is_normal
            # Update info text
            if is_normal:
                lbl_info.Caption = "Normal: Generates random numbers with normal (Gaussian)\ndistribution centered at 'loc' with standard deviation 'scale'."
            else:
                lbl_info.Caption = "Uniform: Generates random numbers with uniform distribution.\nAll values within the range have equal probability."
        
        rb_normal.OnClick = on_type_change
        rb_uniform.OnClick = on_type_change
        
        # Separator
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 330
        sep3.Width = 390
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        # Output options
        lbl_output = vcl.TLabel(Form)
        lbl_output.Parent = Form
        lbl_output.Caption = "Output"
        lbl_output.Left = 10
        lbl_output.Top = 340
        lbl_output.Font.Style = {"fsBold"}
        labels.append(lbl_output)
        
        # Panel to group output radio buttons
        pnl_output = vcl.TPanel(Form)
        pnl_output.Parent = Form
        pnl_output.Left = 10
        pnl_output.Top = 360
        pnl_output.Width = 380
        pnl_output.Height = 30
        pnl_output.BevelOuter = "bvNone"
        
        rb_new = vcl.TRadioButton(Form)
        rb_new.Parent = pnl_output
        rb_new.Caption = "Create new series"
        rb_new.Left = 10
        rb_new.Top = 5
        rb_new.Checked = True
        
        rb_replace = vcl.TRadioButton(Form)
        rb_replace.Parent = pnl_output
        rb_replace.Caption = "Replace original series"
        rb_replace.Left = 190
        rb_replace.Top = 5
        
        # Color for new series
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Color (new series):"
        lbl_color.Left = 20
        lbl_color.Top = 398
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 140
        cb_color.Top = 395
        cb_color.Width = 100
        cb_color.Selected = 0x808080  # Gray by default
        
        # Separator before buttons
        sep4 = vcl.TBevel(Form)
        sep4.Parent = Form
        sep4.Left = 10
        sep4.Top = 430
        sep4.Width = 390
        sep4.Height = 2
        sep4.Shape = "bsTopLine"
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Apply"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 110
        btn_ok.Top = 440
        btn_ok.Width = 100
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 220
        btn_cancel.Top = 440
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # Show dialog
        if Form.ShowModal() == 1:
            try:
                # Get series data
                x_vals = np.array(stats['x_vals'])
                y_vals = np.array(stats['y_vals'])
                n = len(y_vals)
                
                # Generate noise based on selected type
                if rb_normal.Checked:
                    loc = float(edit_loc.Text)
                    scale = float(edit_scale.Text)
                    if scale <= 0:
                        raise ValueError("Standard deviation must be > 0")
                    noise = np.random.normal(loc, scale, n)
                    noise_desc = f"normal(μ={loc}, σ={scale})"
                else:
                    low = float(edit_low.Text)
                    high = float(edit_high.Text)
                    if low >= high:
                        raise ValueError("Lower limit must be < Upper limit")
                    noise = np.random.uniform(low, high, n)
                    noise_desc = f"uniform({low}, {high})"
                
                # Apply noise to Y values
                y_with_noise = y_vals + noise
                
                # Create new points
                new_points = [Point(x, y) for x, y in zip(x_vals, y_with_noise)]
                
                if rb_new.Checked:
                    # Create new series
                    new_series = Graph.TPointSeries()
                    new_series.PointType = point_series.PointType
                    new_series.Points = new_points
                    
                    # Copy display properties
                    original_legend = point_series.LegendText
                    new_series.LegendText = f"{original_legend} [+{noise_desc}]"
                    new_series.Size = point_series.Size
                    new_series.Style = point_series.Style
                    new_series.LineSize = point_series.LineSize
                    new_series.ShowLabels = point_series.ShowLabels
                    
                    # Use selected color
                    color_val = safe_color(cb_color.Selected)
                    new_series.FillColor = color_val
                    new_series.FrameColor = color_val
                    new_series.LineColor = color_val
                    
                    Graph.FunctionList.append(new_series)
                else:
                    # Replace points in original series
                    point_series.Points = new_points
                    original_legend = point_series.LegendText
                    if "[+" not in original_legend:
                        point_series.LegendText = f"{original_legend} [+{noise_desc}]"
                
                Graph.Update()
                
            except ValueError as e:
                show_error(f"Parameter error: {str(e)}", "Noise Generator")
            except Exception as e:
                show_error(f"Error generating noise: {str(e)}", "Noise Generator")
    finally:
        Form.Free()


# Create action for menu
NoiseGeneratorAction = Graph.CreateAction(
    Caption="Noise Generator...",
    IconFile=os.path.join(os.path.dirname(__file__), "Noise_sm.png"),
    OnExecute=add_noise,
    Hint="Adds random noise to the selected point series.",
    ShortCut=""
)

# Add action to 'AWF Generators' submenu under 'Plugins'
Graph.AddActionToMainMenu(NoiseGeneratorAction, TopMenu="Plugins", SubMenus=["Graphîa", "AWF Generators"])
