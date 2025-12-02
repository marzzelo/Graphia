# common/__init__.py
# Shared utilities module for Graph plugins
"""
This module contains common functions and classes used by multiple plugins.
Includes:
- Virtual environment setup
- Functions to get selected point series
- Color conversion utilities
- Helper functions to create point series
"""

import sys
import os

# =============================================================================
# Virtual environment setup
# =============================================================================

def setup_venv():
    """
    Configures Python path to include installed packages.
    Supports both:
    - .packages folder (pip --target installation)
    - .venv virtual environment (legacy)
    
    Must be called before importing external packages like numpy or scipy.
    """
    # Look for packages in the Plugins folder (root)
    plugins_dir = os.path.dirname(os.path.dirname(__file__))
    
    # First try .packages folder (pip --target)
    packages_dir = os.path.join(plugins_dir, ".packages")
    if os.path.exists(packages_dir) and packages_dir not in sys.path:
        sys.path.insert(0, packages_dir)
        return packages_dir
    
    # Fallback to .venv (legacy)
    venv_site_packages = os.path.join(plugins_dir, ".venv", "Lib", "site-packages")
    if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
        sys.path.insert(0, venv_site_packages)
        return venv_site_packages
    
    return None


# Setup venv automatically when importing this module
setup_venv()


# =============================================================================
# Common imports (available after setup_venv)
# =============================================================================

import Graph
import vcl
from collections import namedtuple

# Point type for creating series
Point = namedtuple('Point', ['x', 'y'])


# =============================================================================
# Functions to get selected series
# =============================================================================

def get_selected_point_series():
    """
    Gets the point series selected in the Graph function panel.
    
    Returns:
        tuple: (TPointSeries, None) if there is a valid selected series
               (None, str) with error message if no valid selection
    """
    selected = Graph.Selected
    
    if selected is None:
        return None, "No item selected in the function panel."
    
    # Check if it's a TPointSeries
    if not isinstance(selected, Graph.TPointSeries):
        type_name = type(selected).__name__
        return None, f"The selected item is not a point series (TPointSeries).\nCurrent type: {type_name}"
    
    return selected, None


def require_point_series(plugin_name, min_points=3):
    """
    Gets the selected point series and verifies it has enough points.
    Shows error message if not valid.
    
    Args:
        plugin_name: Plugin name to show in error messages
        min_points: Minimum number of points required (default: 3)
    
    Returns:
        TPointSeries if valid, None if error (message already shown)
    """
    point_series, error_msg = get_selected_point_series()
    
    if point_series is None:
        show_error(error_msg, plugin_name)
        return None
    
    points = point_series.Points
    if not points or len(points) < min_points:
        show_error(
            f"The point series must have at least {min_points} points.",
            plugin_name
        )
        return None
    
    return point_series


# =============================================================================
# Color utilities
# =============================================================================

def safe_color(color_value):
    """
    Converts a color value to a valid integer for TColor.
    Handles special TColorBox values that may cause OverflowError.
    
    Args:
        color_value: Color value (can be from TColorBox.Selected)
    
    Returns:
        int: Valid color value for TColor (24 bits RGB)
    """
    return int(color_value) & 0xFFFFFF


# =============================================================================
# Dialog boxes
# =============================================================================

def show_error(message, title="Error"):
    """
    Shows an error dialog box.
    
    Args:
        message: Error message to show
        title: Window title (default: "Error")
    """
    vcl.Application.MessageBox(
        message,
        f"Error - {title}",
        0x10  # MB_ICONERROR
    )


def show_info(message, title="Information"):
    """
    Shows an informational dialog box.
    
    Args:
        message: Message to show
        title: Window title
    """
    vcl.Application.MessageBox(
        message,
        title,
        0x40  # MB_ICONINFORMATION
    )


def show_warning(message, title="Warning"):
    """
    Shows a warning dialog box.
    
    Args:
        message: Message to show
        title: Window title
    """
    vcl.Application.MessageBox(
        message,
        title,
        0x30  # MB_ICONWARNING
    )


# =============================================================================
# Utilities for creating point series
# =============================================================================

def create_point_series(x_vals, y_vals, legend="", color=0x000000, 
                        line_size=1, copy_style_from=None):
    """
    Creates a new TPointSeries with the given values.
    
    Args:
        x_vals: List or array of X values
        y_vals: List or array of Y values
        legend: Legend text
        color: Series color (default: black)
        line_size: Line width (default: 1)
        copy_style_from: TPointSeries to copy style from (optional)
    
    Returns:
        Graph.TPointSeries: New created series
    """
    points = [Point(x, y) for x, y in zip(x_vals, y_vals)]
    
    new_series = Graph.TPointSeries()
    new_series.Points = points
    new_series.LegendText = legend
    
    if copy_style_from is not None:
        new_series.PointType = copy_style_from.PointType
        new_series.Size = copy_style_from.Size
        new_series.Style = copy_style_from.Style
        new_series.LineSize = copy_style_from.LineSize
        new_series.ShowLabels = copy_style_from.ShowLabels
    else:
        new_series.PointType = Graph.ptCartesian
        new_series.Size = 0
        new_series.Style = 0
        new_series.LineSize = line_size
        new_series.ShowLabels = False
    
    # Apply color (ensuring it's valid)
    safe_col = safe_color(color)
    new_series.FillColor = safe_col
    new_series.FrameColor = safe_col
    new_series.LineColor = safe_col
    
    return new_series


def add_series_to_graph(series):
    """
    Adds a series to the graph and updates the display.
    
    Args:
        series: TPointSeries to add
    """
    Graph.FunctionList.append(series)
    Graph.Update()


# =============================================================================
# Utilities for extracting series data
# =============================================================================

def get_series_data(point_series):
    """
    Extracts X and Y values from a TPointSeries.
    
    Args:
        point_series: TPointSeries to extract data from
    
    Returns:
        tuple: (x_vals, y_vals) as lists
    """
    points = point_series.Points
    x_vals = [p.x for p in points]
    y_vals = [p.y for p in points]
    return x_vals, y_vals


def get_series_stats(point_series):
    """
    Calculates basic statistics for a TPointSeries.
    
    Args:
        point_series: TPointSeries to analyze
    
    Returns:
        dict: Dictionary with statistics (n_points, x_min, x_max, x_range,
              y_min, y_max, y_range, dx_avg)
    """
    points = point_series.Points
    x_vals = [p.x for p in points]
    y_vals = [p.y for p in points]
    
    n = len(points)
    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)
    x_range = x_max - x_min
    y_range = y_max - y_min
    dx_avg = x_range / (n - 1) if n > 1 else 0
    
    return {
        'n_points': n,
        'x_min': x_min,
        'x_max': x_max,
        'x_range': x_range,
        'y_min': y_min,
        'y_max': y_max,
        'y_range': y_range,
        'dx_avg': dx_avg,
        'x_vals': x_vals,
        'y_vals': y_vals
    }


# =============================================================================
# Functions to get multiple series from graph
# =============================================================================

def get_visible_point_series():
    """
    Returns a list of all visible TPointSeries in the graph.
    
    Returns:
        list: List of TPointSeries objects that are visible
    """
    series_list = []
    for item in Graph.FunctionList:
        if type(item).__name__ == "TPointSeries" and item.Visible:
            series_list.append(item)
    return series_list


def get_all_point_series():
    """
    Returns a list of ALL TPointSeries in the graph (visible or not).
    
    Returns:
        list: List of all TPointSeries objects
    """
    series_list = []
    for item in Graph.FunctionList:
        if type(item).__name__ == "TPointSeries":
            series_list.append(item)
    return series_list


# =============================================================================
# Numpy-based data extraction (requires numpy)
# =============================================================================

def get_series_data_np(point_series):
    """
    Extracts X and Y values from a TPointSeries as numpy arrays.
    
    Note: Requires numpy to be imported. Call setup_venv() first if using
    from a module that hasn't set up the virtual environment.
    
    Args:
        point_series: TPointSeries to extract data from
    
    Returns:
        tuple: (x_array, y_array) as numpy arrays
    """
    import numpy as np
    points = point_series.Points
    x = np.array([p.x for p in points])
    y = np.array([p.y for p in points])
    return x, y


def resample_to_base(x_base, x_target, y_target, method='cubic'):
    """
    Resamples target series Y values to match base series X positions.
    Uses interpolation to calculate Y values at the base X positions.
    
    Note: Requires numpy and scipy to be imported.
    
    Args:
        x_base: X values of the base series (defines output X positions)
        x_target: X values of the target series
        y_target: Y values of the target series
        method: Interpolation method ('cubic', 'linear'). Default: 'cubic'
        
    Returns:
        numpy.ndarray: Resampled Y values at x_base positions.
                       NaN values where extrapolation would be needed.
    """
    import numpy as np
    from scipy.interpolate import CubicSpline
    
    # Sort target data by X (required for interpolation)
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
    
    if method == 'cubic':
        try:
            cs = CubicSpline(x_unique, y_unique, extrapolate=False)
            y_resampled = cs(x_base)
        except Exception:
            # Fallback to linear interpolation
            y_resampled = np.interp(x_base, x_unique, y_unique)
    else:
        # Linear interpolation
        y_resampled = np.interp(x_base, x_unique, y_unique)
        # Mark extrapolated values as NaN
        y_resampled = np.where(
            (x_base < x_unique.min()) | (x_base > x_unique.max()),
            np.nan,
            y_resampled
        )
    
    return y_resampled


# =============================================================================
# Text utilities
# =============================================================================

def sanitize_legend(legend):
    """
    Sanitizes a legend string for use as a column header or filename.
    Removes or replaces characters that might cause issues.
    
    Args:
        legend: Original legend text
        
    Returns:
        str: Sanitized legend text
    """
    if not legend:
        return "Unnamed"
    # Replace problematic characters
    sanitized = legend.replace('"', "'").replace('\n', ' ').replace('\r', '')
    return sanitized.strip() or "Unnamed"


# =============================================================================
# Standard color palette for series
# =============================================================================

SERIES_COLORS = [
    0x0000FF,  # Red (BGR)
    0x00AA00,  # Green
    0xFF0000,  # Blue
    0x00AAAA,  # Yellow (dark)
    0xAA00AA,  # Magenta
    0xAAAA00,  # Cyan
    0x0055AA,  # Orange
    0x880088,  # Purple
    0x008800,  # Dark Green
    0x000088,  # Dark Red
    0x444444,  # Dark Gray
    0x008888,  # Olive
]
