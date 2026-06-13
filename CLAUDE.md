# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A collection of Python plugins for the [Graph](https://www.padowan.dk/) plotting application (v4.4), extending it with signal analysis, filtering, importing/exporting, morphing, visualization, and waveform generation. Graph embeds **Python 3.7** and exposes a `Graph` module and `vcl` (Visual Component Library) for building plugin UIs.

## Plugin Architecture

Plugins are organized in category folders. Each category has a top-level `__init__.py` that imports sub-plugins with protected `try/except` blocks so one broken plugin doesn't disable the whole category:

```python
# category/__init__.py pattern
try:
    from . import my_plugin
except ImportError:
    pass
```

Each individual plugin lives in its own subdirectory with `__init__.py` and declares:
- `PluginName`, `PluginVersion`, `PluginDescription` module-level variables
- A callback function (receives an `Action` parameter from Graph)

**Disabling a plugin**: rename `__init__.py` → `__init__.py.disabled`. The `PluginManager` plugin does this via UI.

## Common Module (`common/__init__.py`)

Every plugin that uses external packages must start with:
```python
from common import setup_venv  # or just: import common
```
`common` auto-calls `setup_venv()` on import, adding `.packages/` (or `.venv/Lib/site-packages/`) to `sys.path` before any numpy/scipy import.

Key utilities in `common`:
- `require_point_series(plugin_name, min_points)` — validates Graph selection, shows error and returns `None` on failure
- `get_selected_point_series()` → `(TPointSeries | None, error_str | None)`
- `get_series_data(series)` → `(x_list, y_list)`
- `create_point_series(x_vals, y_vals, legend, color, ...)` — adds a new series to the Graph
- `get_visible_point_series()`, `get_all_point_series()` — bulk retrieval
- `show_error(msg)`, `show_info(msg)`, `show_warning(msg)` — VCL dialog wrappers
- `SERIES_COLORS` — 12-color standard palette

## Graph API

```python
import Graph
import vcl

Graph.Selected          # currently selected item in the function panel
Graph.TPointSeries      # type to check against
vcl.TForm(None)         # create a modal dialog
vcl.TLabel(form)        # add label
vcl.TEdit(form)         # add input field
vcl.TButton(form)       # add button
form.ShowModal()        # display dialog
```

## Environment & Dependencies

- **Runtime**: Graph's embedded Python at `..\Python\python.exe` (relative to Plugins folder)
- **Packages**: installed to `.packages/` via `pip install --target .packages -r requirements.txt`
- **Key deps**: numpy 1.21.6, scipy 1.7.3, openai, pydantic (<2.0.0), python-dotenv, Pillow

Install dependencies:
```powershell
# From the Plugins directory
& "..\Python\python.exe" -m pip install --target .packages -r requirements.txt
```

Or run the installer:
```powershell
.\install.ps1   # PowerShell
# or
install.bat     # Command Prompt
```

## Creating a New Plugin

1. Create `<category>/<plugin_name>/__init__.py`
2. Add `from . import <plugin_name>` (wrapped in try/except) to `<category>/__init__.py`
3. Import `common` first, then external packages
4. Retrieve and validate the user's Graph selection with `require_point_series()`
5. Build VCL dialog if needed, then compute and call `create_point_series()` to output results

## AI Waveform Generator

The `wfgen/AIFunctionGenerator` plugin uses OpenAI (GPT models). Requires `OPENAI_API_KEY` in a `.env` file at the Plugins root (see `.env.example`). The plugin also accepts the key at runtime via a dialog. Uses Pydantic for structured output validation.

## Test Data

Example `.grf` Graph files for testing plugins are in `docs/`.
