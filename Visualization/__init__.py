"""
GetVisibleRect - Plugin to draw a visible area rectangle
Draws a rectangle that matches the current axis limits.
"""

import Graph
import vcl
import os
from collections import namedtuple

Point = namedtuple('Point', ['x', 'y'])


def DrawVisibleRect(Action):
    """
    Draws a rectangle matching the current visible area.
    """
    # Get current axis limits
    x_min = Graph.Axes.xAxis.Min
    x_max = Graph.Axes.xAxis.Max
    y_min = Graph.Axes.yAxis.Min
    y_max = Graph.Axes.yAxis.Max
    
    # Define the 5 rectangle points (close the loop)
    points = [
        Point(x_min, y_min),
        Point(x_max, y_min),
        Point(x_max, y_max),
        Point(x_min, y_max),
        Point(x_min, y_min)
    ]
    
    # Create point series
    rect_series = Graph.TPointSeries()
    rect_series.Points = points
    rect_series.LegendText = "Visible Area"
    
    # Configure style
    rect_series.Size = 0          # No markers
    rect_series.Style = 0         # Marker style (irrelevant if Size=0)
    rect_series.LineSize = 2      # Line width
    
    # Dark Gray color
    rect_series.LineColor = 0x404040
    rect_series.FillColor = 0x404040
    
    # Dashed line style
    try:
        rect_series.LineStyle = Graph.psDash
    except AttributeError:
        rect_series.LineStyle = 2  # 2 is dotted line
        
    rect_series.ShowLabels = False
    
    # Add to function list and update
    Graph.FunctionList.append(rect_series)
    Graph.Update()


# Register action
Action = Graph.CreateAction(
    Caption="Draw Visible Rectangle",
    OnExecute=DrawVisibleRect,
    Hint="Draws a rectangle matching the current visible area",
    IconFile=os.path.join(os.path.dirname(__file__), "VisibleRect_sm.png")
)

# Add to Plugins -> Visualization menu
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "Visualization"])
