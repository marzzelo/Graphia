# Plugin to sample a function at discrete points
# Generates a TPointSeries from the evaluation of f(x) at x_i = t0 + i*Ts
import os
import math

# Import common module (automatically configures venv)
from common import (
    show_error, safe_color, Point, Graph, vcl,
    get_selected_function, get_function_info, sample_std_function
)

PluginName = "Function Sampler"
PluginVersion = "1.0"
PluginDescription = "Samples the selected function at discrete points with a given sampling period."

def sample_function(Action):
    """Samples the selected function at discrete points (dialog interface)."""
    
    # Check that a TStdFunc is selected
    func, error_msg = get_selected_function()
    
    if func is None:
        show_error(error_msg, "Function Sampler")
        return
    
    # Get function properties using helper from common
    try:
        func_info = get_function_info(func)
        func_text = func_info['text']
        x_from = func_info['x_from']
        x_to = func_info['x_to']
    except Exception:
        func_text = "unknown"
        x_from = -10.0
        x_to = 10.0
    
    x_range = x_to - x_from
    # Suggest sampling period as 1% of the range
    suggested_ts = x_range / 100.0 if x_range > 0 else 0.1
    
    # Create configuration form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "Function Sampler"
        Form.Width = 420
        Form.Height = 410
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
        lbl_help_title.Caption = "Function Sampler"
        lbl_help_title.Left = 10
        lbl_help_title.Top = 8
        lbl_help_title.Font.Style = {"fsBold"}
        lbl_help_title.Font.Color = 0x804000
        labels.append(lbl_help_title)

        lbl_help = vcl.TLabel(help_panel)
        lbl_help.Parent = help_panel
        lbl_help.Caption = "Generates: yᵢ = f(xᵢ),  xᵢ = t₀ + i·Ts"
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
        
        # Function info section
        lbl_func = vcl.TLabel(Form)
        lbl_func.Parent = Form
        lbl_func.Caption = "Selected Function"
        lbl_func.Left = 10
        lbl_func.Top = 85
        lbl_func.Font.Style = {"fsBold"}
        labels.append(lbl_func)
        
        # Function equation display
        lbl_equation = vcl.TLabel(Form)
        lbl_equation.Parent = Form
        lbl_equation.Caption = f"f(x) = {func_text}"
        lbl_equation.Left = 20
        lbl_equation.Top = 108
        lbl_equation.Font.Color = 0x0000AA
        labels.append(lbl_equation)
        
        # Function interval
        lbl_interval = vcl.TLabel(Form)
        lbl_interval.Parent = Form
        lbl_interval.Caption = f"Interval: [{x_from:.4g}, {x_to:.4g}]"
        lbl_interval.Left = 20
        lbl_interval.Top = 128
        lbl_interval.Font.Color = 0x666666
        labels.append(lbl_interval)
        
        # Separator
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 155
        sep2.Width = 390
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        # Sampling parameters section
        lbl_params = vcl.TLabel(Form)
        lbl_params.Parent = Form
        lbl_params.Caption = "Sampling Parameters"
        lbl_params.Left = 10
        lbl_params.Top = 165
        lbl_params.Font.Style = {"fsBold"}
        labels.append(lbl_params)
        
        # Sampling period
        lbl_ts = vcl.TLabel(Form)
        lbl_ts.Parent = Form
        lbl_ts.Caption = "Sampling Period (Ts):"
        lbl_ts.Left = 20
        lbl_ts.Top = 193
        labels.append(lbl_ts)
        
        edit_ts = vcl.TEdit(Form)
        edit_ts.Parent = Form
        edit_ts.Left = 160
        edit_ts.Top = 190
        edit_ts.Width = 80
        edit_ts.Text = f"{suggested_ts:.6g}"
        
        # Start time
        lbl_t0 = vcl.TLabel(Form)
        lbl_t0.Parent = Form
        lbl_t0.Caption = "Start Time (t₀):"
        lbl_t0.Left = 20
        lbl_t0.Top = 223
        labels.append(lbl_t0)
        
        edit_t0 = vcl.TEdit(Form)
        edit_t0.Parent = Form
        edit_t0.Left = 160
        edit_t0.Top = 220
        edit_t0.Width = 80
        edit_t0.Text = f"{x_from:.6g}"
        
        # End time
        lbl_tf = vcl.TLabel(Form)
        lbl_tf.Parent = Form
        lbl_tf.Caption = "End Time (tf):"
        lbl_tf.Left = 20
        lbl_tf.Top = 253
        labels.append(lbl_tf)
        
        edit_tf = vcl.TEdit(Form)
        edit_tf.Parent = Form
        edit_tf.Left = 160
        edit_tf.Top = 250
        edit_tf.Width = 80
        edit_tf.Text = f"{x_to:.6g}"
        
        # Points count info label
        lbl_count = vcl.TLabel(Form)
        lbl_count.Parent = Form
        lbl_count.Caption = ""
        lbl_count.Left = 260
        lbl_count.Top = 193
        lbl_count.Font.Color = 0x808080
        labels.append(lbl_count)
        
        def update_count(Sender):
            try:
                ts = float(edit_ts.Text)
                t0 = float(edit_t0.Text)
                tf = float(edit_tf.Text)
                if ts > 0 and tf > t0:
                    count = int((tf - t0) / ts) + 1
                    lbl_count.Caption = f"≈ {count} points"
                else:
                    lbl_count.Caption = "(invalid)"
            except:
                lbl_count.Caption = "(error)"
        
        edit_ts.OnChange = update_count
        edit_t0.OnChange = update_count
        edit_tf.OnChange = update_count
        update_count(None)  # Initial update
        
        # Color for new series
        lbl_color = vcl.TLabel(Form)
        lbl_color.Parent = Form
        lbl_color.Caption = "Series Color:"
        lbl_color.Left = 20
        lbl_color.Top = 288
        labels.append(lbl_color)
        
        cb_color = vcl.TColorBox(Form)
        cb_color.Parent = Form
        cb_color.Left = 160
        cb_color.Top = 285
        cb_color.Width = 100
        cb_color.Selected = 0x0000FF  # Red by default
        
        # Separator before buttons
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 320
        sep3.Width = 390
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "Sample"
        btn_ok.ModalResult = 1  # mrOk
        btn_ok.Default = True
        btn_ok.Left = 110
        btn_ok.Top = 330
        btn_ok.Width = 100
        btn_ok.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.ModalResult = 2  # mrCancel
        btn_cancel.Cancel = True
        btn_cancel.Left = 220
        btn_cancel.Top = 330
        btn_cancel.Width = 100
        btn_cancel.Height = 30
        
        # Show dialog
        if Form.ShowModal() == 1:
            try:
                # Get parameters from dialog
                ts = float(edit_ts.Text)
                t0 = float(edit_t0.Text)
                tf = float(edit_tf.Text)
                
                # Use the decoupled sampling function from common
                x_vals, y_vals, errors = sample_std_function(func, ts, t0, tf)
                
                # Filter out NaN values
                valid_points = [(x, y) for x, y in zip(x_vals, y_vals) if not math.isnan(y)]
                
                if not valid_points:
                    raise ValueError("No valid points could be generated. Check the function and interval.")
                
                # Create points
                points = [Point(x, y) for x, y in valid_points]
                
                # Get color
                color_val = safe_color(cb_color.Selected)
                
                # Create new series
                new_series = Graph.TPointSeries()
                new_series.PointType = Graph.ptCartesian
                new_series.Points = points
                
                # Build legend
                legend_text = f"Sampled: {func_text} (Ts={ts:.4g})"
                new_series.LegendText = legend_text
                
                new_series.Size = 2  # Marker size
                new_series.Style = 0  # Circle marker style
                new_series.LineSize = 1
                new_series.ShowLabels = False
                
                new_series.FillColor = color_val
                new_series.FrameColor = color_val
                new_series.LineColor = color_val
                
                Graph.FunctionList.append(new_series)
                Graph.Update()
                
            except ValueError as e:
                show_error(f"Parameter error: {str(e)}", "Function Sampler")
            except Exception as e:
                show_error(f"Error sampling function: {str(e)}", "Function Sampler")
    finally:
        Form.Free()


# Create action for menu
FunctionSamplerAction = Graph.CreateAction(
    Caption="Function Sampler...",
    IconFile=os.path.join(os.path.dirname(__file__), "FunctionSampler_sm.png"),
    OnExecute=sample_function,
    Hint="Samples the selected function at discrete points.",
    ShortCut=""
)

# Add action to 'AWF Generators' submenu under 'Plugins'
Graph.AddActionToMainMenu(FunctionSamplerAction, TopMenu="Plugins", SubMenus=["Graphîa", "AWF Generators"]) # type: ignore
