# exporting/CSVExporter/__init__.py
"""
CSVExporter - Plugin to export visible point series to CSV format.
The selected (base) series defines the sampling period and limits.
Other series are resampled using cubic interpolation to match the base series.
"""

import os
import Graph
import vcl

# Import common utilities
from common import (
    setup_venv, show_error, show_info, safe_color, Point
)

# Setup venv for scipy
setup_venv()

import numpy as np
from scipy.interpolate import CubicSpline

PluginName = "CSV Exporter"
PluginVersion = "1.0"
PluginDescription = "Exports visible point series to CSV format with resampling."

# Default settings
DEFAULT_SEPARATOR = ','
DEFAULT_DECIMALS = 6


def get_visible_point_series():
    """
    Returns a list of all visible TPointSeries in the graph.
    
    Returns:
        list: List of tuples (series, legend_text) for visible point series
    """
    series_list = []
    
    for item in Graph.FunctionList:
        if isinstance(item, Graph.TPointSeries):
            # Check if series is visible
            if hasattr(item, 'Visible') and not item.Visible:
                continue
            
            legend = item.LegendText or f"Series_{len(series_list)+1}"
            series_list.append((item, legend))
    
    return series_list


def get_series_xy(series):
    """
    Extracts X and Y arrays from a TPointSeries.
    
    Args:
        series: TPointSeries object
        
    Returns:
        tuple: (x_array, y_array) as numpy arrays
    """
    points = series.Points
    x = np.array([p.x for p in points])
    y = np.array([p.y for p in points])
    return x, y


def resample_series(x_base, y_base, x_target, y_target):
    """
    Resamples target series to match base series X values using cubic interpolation.
    
    Args:
        x_base: X values of the base series (defines output X)
        y_base: Y values of the base series (not used, but kept for clarity)
        x_target: X values of the target series
        y_target: Y values of the target series
        
    Returns:
        numpy.ndarray: Resampled Y values at x_base positions
    """
    # Sort target data by X (required for CubicSpline)
    sort_idx = np.argsort(x_target)
    x_sorted = x_target[sort_idx]
    y_sorted = y_target[sort_idx]
    
    # Remove duplicates (keep first occurrence)
    _, unique_idx = np.unique(x_sorted, return_index=True)
    x_unique = x_sorted[unique_idx]
    y_unique = y_sorted[unique_idx]
    
    if len(x_unique) < 2:
        # Cannot interpolate with less than 2 points
        return np.full_like(x_base, np.nan, dtype=float)
    
    # Create cubic spline interpolator
    try:
        cs = CubicSpline(x_unique, y_unique, extrapolate=False)
        y_resampled = cs(x_base)
    except Exception:
        # Fallback to linear interpolation
        y_resampled = np.interp(x_base, x_unique, y_unique)
    
    return y_resampled


def export_to_csv(file_path, separator, columns_config, include_sample_index):
    """
    Exports the configured series to a CSV file.
    
    Args:
        file_path: Full path to the output CSV file
        separator: Column separator character
        columns_config: List of dicts with keys:
            - series: TPointSeries object (None for base X column)
            - legend: Column header name
            - decimals: Number of decimal places
            - order: Column order (1-based)
            - is_base: True if this is the base series
            - is_x: True if this is the X column (time)
        include_sample_index: If True, include Sample# as first column
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Find base series
        base_config = next((c for c in columns_config if c.get('is_base')), None)
        if not base_config:
            return False, "No base series selected."
        
        base_series = base_config['series']
        x_base, y_base = get_series_xy(base_series)
        
        # Sort base by X
        sort_idx = np.argsort(x_base)
        x_base = x_base[sort_idx]
        y_base = y_base[sort_idx]
        
        n_samples = len(x_base)
        
        # Build columns in order
        # Filter active columns and sort by order
        active_cols = [c for c in columns_config if c.get('include', True)]
        active_cols.sort(key=lambda c: c.get('order', 999))
        
        # Prepare data columns
        headers = []
        data_columns = []
        
        # Add sample index if requested
        if include_sample_index:
            headers.append("Sample#")
            data_columns.append(np.arange(1, n_samples + 1))
        
        for col in active_cols:
            headers.append(col['legend'])
            decimals = col.get('decimals', DEFAULT_DECIMALS)
            
            if col.get('is_x'):
                # This is the X (time) column from base series
                data_columns.append((x_base, decimals))
            elif col.get('is_base'):
                # This is the Y column from base series
                data_columns.append((y_base, decimals))
            else:
                # Resample this series to match base X
                series = col['series']
                x_target, y_target = get_series_xy(series)
                y_resampled = resample_series(x_base, y_base, x_target, y_target)
                data_columns.append((y_resampled, decimals))
        
        # Write CSV file
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write header
            f.write(separator.join(headers) + '\n')
            
            # Write data rows
            for i in range(n_samples):
                row_values = []
                for col_data in data_columns:
                    if isinstance(col_data, np.ndarray):
                        # Sample index (integer)
                        row_values.append(str(int(col_data[i])))
                    else:
                        # (values_array, decimals)
                        values, decimals = col_data
                        val = values[i]
                        if np.isnan(val):
                            row_values.append("")
                        else:
                            row_values.append(f"{val:.{decimals}f}")
                
                f.write(separator.join(row_values) + '\n')
        
        return True, f"Exported {n_samples} samples to {file_path}"
        
    except Exception as e:
        return False, f"Export error: {str(e)}"


def sanitize_legend(legend):
    """
    Sanitizes a legend string for use as a column header.
    Removes or replaces characters that might cause issues in CSV.
    """
    # Replace problematic characters
    sanitized = legend.replace('"', "'").replace('\n', ' ').replace('\r', '')
    return sanitized.strip() or "Unnamed"


class SeriesConfigRow:
    """
    UI row for configuring a single series in the export dialog.
    """
    def __init__(self, parent, top, series, legend, is_base=False, is_x_column=False):
        self.series = series
        self.is_base = is_base
        self.is_x_column = is_x_column
        self.original_legend = legend
        
        # Include checkbox
        self.chk_include = vcl.TCheckBox(parent)
        self.chk_include.Parent = parent
        self.chk_include.Left = 10
        self.chk_include.Top = top
        self.chk_include.Width = 20
        self.chk_include.Checked = True
        
        # Series name (editable)
        self.edt_name = vcl.TEdit(parent)
        self.edt_name.Parent = parent
        self.edt_name.Left = 35
        self.edt_name.Top = top - 2
        self.edt_name.Width = 180
        self.edt_name.Text = sanitize_legend(legend)
        
        # Decimals (spinner)
        self.edt_decimals = vcl.TEdit(parent)
        self.edt_decimals.Parent = parent
        self.edt_decimals.Left = 225
        self.edt_decimals.Top = top - 2
        self.edt_decimals.Width = 50
        self.edt_decimals.Text = "6" if not is_x_column else "6"
        
        # Disable decimals for Sample# (if we add it)
        if is_x_column:
            self.edt_decimals.Text = "6"
        
        # Order (spinner)
        self.edt_order = vcl.TEdit(parent)
        self.edt_order.Parent = parent
        self.edt_order.Left = 285
        self.edt_order.Top = top - 2
        self.edt_order.Width = 40
        self.edt_order.Text = ""
        
        # Base indicator
        self.lbl_base = vcl.TLabel(parent)
        self.lbl_base.Parent = parent
        self.lbl_base.Left = 335
        self.lbl_base.Top = top
        self.lbl_base.Caption = "(base)" if is_base else ""
        self.lbl_base.Font.Color = 0x008800  # Green
    
    def get_config(self):
        """Returns the configuration dict for this row."""
        try:
            decimals = int(self.edt_decimals.Text)
        except ValueError:
            decimals = DEFAULT_DECIMALS
        
        try:
            order = int(self.edt_order.Text) if self.edt_order.Text.strip() else 999
        except ValueError:
            order = 999
        
        return {
            'series': self.series,
            'legend': self.edt_name.Text,
            'decimals': decimals,
            'order': order,
            'include': self.chk_include.Checked,
            'is_base': self.is_base,
            'is_x': self.is_x_column
        }
    
    def set_order(self, order):
        """Sets the order value."""
        self.edt_order.Text = str(order)


def csv_export_dialog(Action):
    """
    Shows the CSV export configuration dialog.
    """
    # Get all visible point series
    visible_series = get_visible_point_series()
    
    if len(visible_series) < 1:
        show_error(
            "No visible point series found.\n"
            "Please add at least one point series to the graph.",
            "CSV Exporter"
        )
        return
    
    # Check if there's a selected series (will be the base)
    selected = Graph.Selected
    base_series = None
    base_legend = None
    
    if selected and isinstance(selected, Graph.TPointSeries):
        for series, legend in visible_series:
            if series is selected:
                base_series = series
                base_legend = legend
                break
    
    # If no selection, use first series as base
    if base_series is None:
        base_series, base_legend = visible_series[0]
    
    # Create dialog
    Form = vcl.TForm(None)
    try:
        Form.Caption = "CSV Exporter"
        Form.Width = 500
        Form.Height = 500
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        # Title
        lbl_title = vcl.TLabel(Form)
        lbl_title.Parent = Form
        lbl_title.Caption = "Export Point Series to CSV"
        lbl_title.Left = 20
        lbl_title.Top = 10
        lbl_title.Font.Style = {"fsBold"}
        lbl_title.Font.Size = 10
        
        # Base series info
        x_base, y_base = get_series_xy(base_series)
        n_points = len(x_base)
        x_min, x_max = np.min(x_base), np.max(x_base)
        dx_avg = np.mean(np.diff(np.sort(x_base))) if n_points > 1 else 0
        
        lbl_base_info = vcl.TLabel(Form)
        lbl_base_info.Parent = Form
        lbl_base_info.Caption = (
            f"Base series: {base_legend}  |  "
            f"Points: {n_points}  |  X: [{x_min:.4g}, {x_max:.4g}]  |  ΔT ≈ {dx_avg:.4g}"
        )
        lbl_base_info.Left = 20
        lbl_base_info.Top = 35
        lbl_base_info.Font.Color = 0x666666
        
        # Separator
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 55
        sep1.Width = 470
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Separator selector
        lbl_sep = vcl.TLabel(Form)
        lbl_sep.Parent = Form
        lbl_sep.Caption = "Separator:"
        lbl_sep.Left = 20
        lbl_sep.Top = 67
        
        cb_separator = vcl.TComboBox(Form)
        cb_separator.Parent = Form
        cb_separator.Left = 90
        cb_separator.Top = 64
        cb_separator.Width = 70
        cb_separator.Style = "csDropDownList"
        cb_separator.Items.Add(",")
        cb_separator.Items.Add(";")
        cb_separator.Items.Add("\\t")
        cb_separator.Items.Add("|")
        cb_separator.ItemIndex = 0
        
        # Include Sample# checkbox
        chk_sample_idx = vcl.TCheckBox(Form)
        chk_sample_idx.Parent = Form
        chk_sample_idx.Left = 180
        chk_sample_idx.Top = 67
        chk_sample_idx.Width = 150
        chk_sample_idx.Caption = "Include Sample# column"
        chk_sample_idx.Checked = False
        
        # Column headers
        lbl_include = vcl.TLabel(Form)
        lbl_include.Parent = Form
        lbl_include.Caption = "Include"
        lbl_include.Left = 10
        lbl_include.Top = 95
        lbl_include.Font.Style = {"fsBold"}
        
        lbl_name_hdr = vcl.TLabel(Form)
        lbl_name_hdr.Parent = Form
        lbl_name_hdr.Caption = "Column Name"
        lbl_name_hdr.Left = 55
        lbl_name_hdr.Top = 95
        lbl_name_hdr.Font.Style = {"fsBold"}
        
        lbl_dec_hdr = vcl.TLabel(Form)
        lbl_dec_hdr.Parent = Form
        lbl_dec_hdr.Caption = "Decimals"
        lbl_dec_hdr.Left = 225
        lbl_dec_hdr.Top = 95
        lbl_dec_hdr.Font.Style = {"fsBold"}
        
        lbl_order_hdr = vcl.TLabel(Form)
        lbl_order_hdr.Parent = Form
        lbl_order_hdr.Caption = "Order"
        lbl_order_hdr.Left = 285
        lbl_order_hdr.Top = 95
        lbl_order_hdr.Font.Style = {"fsBold"}
        
        # Scrollbox for series list
        scroll_box = vcl.TScrollBox(Form)
        scroll_box.Parent = Form
        scroll_box.Left = 10
        scroll_box.Top = 115
        scroll_box.Width = 470
        scroll_box.Height = 200
        scroll_box.BorderStyle = "bsSingle"
        
        # Create series rows
        series_rows = []
        row_top = 5
        row_height = 28
        order_counter = 1
        
        # First: X column (time) from base series
        x_row = SeriesConfigRow(
            scroll_box, row_top, base_series, 
            "time", is_base=False, is_x_column=True
        )
        x_row.set_order(order_counter)
        order_counter += 1
        series_rows.append(x_row)
        row_top += row_height
        
        # Then: all Y series (base first, then others)
        # Base series Y
        base_row = SeriesConfigRow(
            scroll_box, row_top, base_series,
            base_legend, is_base=True, is_x_column=False
        )
        base_row.set_order(order_counter)
        order_counter += 1
        series_rows.append(base_row)
        row_top += row_height
        
        # Other series
        for series, legend in visible_series:
            if series is not base_series:
                other_row = SeriesConfigRow(
                    scroll_box, row_top, series,
                    legend, is_base=False, is_x_column=False
                )
                other_row.set_order(order_counter)
                order_counter += 1
                series_rows.append(other_row)
                row_top += row_height
        
        # Separator
        sep2 = vcl.TBevel(Form)
        sep2.Parent = Form
        sep2.Left = 10
        sep2.Top = 325
        sep2.Width = 470
        sep2.Height = 2
        sep2.Shape = "bsTopLine"
        
        # File path
        lbl_path = vcl.TLabel(Form)
        lbl_path.Parent = Form
        lbl_path.Caption = "Save to:"
        lbl_path.Left = 20
        lbl_path.Top = 340
        
        # Default path: current document path or user's Documents
        default_path = ""
        if Graph.Data and hasattr(Graph.Data, 'FileName') and Graph.Data.FileName:
            default_path = os.path.dirname(Graph.Data.FileName)
        if not default_path:
            default_path = os.path.expanduser("~/Documents")
        
        default_filename = "export.csv"
        default_full_path = os.path.join(default_path, default_filename)
        
        edt_filepath = vcl.TEdit(Form)
        edt_filepath.Parent = Form
        edt_filepath.Left = 20
        edt_filepath.Top = 360
        edt_filepath.Width = 400
        edt_filepath.Text = default_full_path
        
        # Browse button
        btn_browse = vcl.TButton(Form)
        btn_browse.Parent = Form
        btn_browse.Caption = "..."
        btn_browse.Left = 425
        btn_browse.Top = 358
        btn_browse.Width = 35
        btn_browse.Height = 25
        
        def on_browse_click(Sender):
            save_dialog = vcl.TSaveDialog(Form)
            save_dialog.Title = "Save CSV File"
            save_dialog.Filter = "CSV Files (*.csv)|*.csv|All Files (*.*)|*.*"
            save_dialog.DefaultExt = "csv"
            save_dialog.FileName = os.path.basename(edt_filepath.Text)
            save_dialog.InitialDir = os.path.dirname(edt_filepath.Text)
            
            if save_dialog.Execute():
                edt_filepath.Text = save_dialog.FileName
        
        btn_browse.OnClick = on_browse_click
        
        # Separator
        sep3 = vcl.TBevel(Form)
        sep3.Parent = Form
        sep3.Left = 10
        sep3.Top = 400
        sep3.Width = 470
        sep3.Height = 2
        sep3.Shape = "bsTopLine"
        
        # Buttons
        btn_export = vcl.TButton(Form)
        btn_export.Parent = Form
        btn_export.Caption = "Export"
        btn_export.Left = 300
        btn_export.Top = 420
        btn_export.Width = 80
        btn_export.Height = 30
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.Left = 390
        btn_cancel.Top = 420
        btn_cancel.Width = 80
        btn_cancel.Height = 30
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        
        def on_export_click(Sender):
            # Get separator
            sep_text = cb_separator.Text
            if sep_text == "\\t":
                separator = "\t"
            else:
                separator = sep_text
            
            # Get file path
            file_path = edt_filepath.Text.strip()
            if not file_path:
                show_error("Please specify a file path.", "CSV Exporter")
                return
            
            # Ensure .csv extension
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'
            
            # Check directory exists
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except Exception as e:
                    show_error(f"Cannot create directory: {e}", "CSV Exporter")
                    return
            
            # Collect column configurations
            columns_config = [row.get_config() for row in series_rows]
            
            # Check at least one column is selected
            active_cols = [c for c in columns_config if c['include']]
            if not active_cols:
                show_error("Please select at least one column to export.", "CSV Exporter")
                return
            
            # Export
            include_sample = chk_sample_idx.Checked
            success, message = export_to_csv(file_path, separator, columns_config, include_sample)
            
            if success:
                show_info(message, "CSV Exporter")
                Form.ModalResult = 1
            else:
                show_error(message, "CSV Exporter")
        
        btn_export.OnClick = on_export_click
        
        Form.ShowModal()
        
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="CSV Exporter...",
    OnExecute=csv_export_dialog,
    Hint="Export visible point series to CSV format",
)

# Add to Plugins menu -> Graphîa -> Exporting
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Exporting"])
