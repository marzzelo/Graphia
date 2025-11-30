# Graph Plugin System

<div align="center">
    <img src="screenshots/logo_ia.png" alt="Graph Plugin System Logo">
    <br>
    <br>
</div>

![Python](https://img.shields.io/badge/Python-3.7-3776AB?style=flat&logo=python&logoColor=white)
![Graph](https://img.shields.io/badge/Graph-4.4-green?style=flat)
![NumPy](https://img.shields.io/badge/NumPy-1.21.6-013243?style=flat&logo=numpy&logoColor=white)
![SciPy](https://img.shields.io/badge/SciPy-1.7.3-8CAAE6?style=flat&logo=scipy&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?style=flat&logo=openai&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

A comprehensive collection of Python plugins designed for the [Graph](https://www.padowan.dk/) plotting application. This system extends the functionality of Graph by adding advanced filtering, data importing, signal morphing, visualization tools, and waveform generation capabilities.

---

## 📑 Table of Contents

- [Installation](#-installation)
- [Development Setup](#-development-setup)
- [1. Filters](#1-filters)
  - [Gaussian Filter](#-gaussian-filter)
  - [Selective Median Filter](#-selective-median-filter)
- [2. Importing](#2-importing)
  - [Advanced CSV Importer](#-advanced-csv-importer)
  - [Profile Manager](#-profile-manager)
- [3. Morphing](#3-morphing)
  - [Morph - Transform Series](#-morph---transform-series)
  - [Resample](#-resample)
  - [Signal Info](#-signal-info)
  - [Apply Function](#-apply-function)
  - [Linear Combination](#-linear-combination)
- [4. Visualization](#4-visualization)
  - [Draw Visible Rect](#-draw-visible-rect)
- [5. Waveform Generation](#5-waveform-generation-wfgen)
  - [Composite Signal Generator](#️-composite-signal-generator)
  - [AI Function Generator](#-ai-function-generator)
  - [Spike Generator](#-spike-generator)
  - [Noise Generator](#-noise-generator)
  - [Function Sampler](#-function-sampler)
- [Utilities](#️-utilities)
- [Author](#-author)
- [License](#-license)

---

## 📥 Installation

### Quick Install (Recommended)

1. **Download** the latest release `.zip` from [GitHub Releases](https://github.com/marzzelo/graph-plugins/releases).
2. **Extract** the contents into Graph's `Plugins` folder:
   - `C:\Program Files (x86)\Graph\Plugins` (All users, requires Admin)
   - or `C:\Users\<YourUsername>\AppData\Local\Graph\Plugins` (Current user only)
3. **Run the installer** to set up the Python environment:
   - Double-click `install.bat` (Command Prompt)
   - Or right-click `install.ps1` → "Run with PowerShell"
4. **Restart Graph**. The plugins will be automatically loaded.

> **Note**: The installer creates a `.packages` folder with all required Python packages. This requires an internet connection.

### Manual Installation

Choose one of the following plugin locations:

1.  **All Users** (Requires Administrator privileges):
    *   `C:\Program Files (x86)\Graph\Plugins`
2.  **Current User Only**:
    *   `C:\Users\<YourUsername>\AppData\Local\Graph\Plugins`

Then create the packages folder manually (see Development Setup below).

---

## 💻 Development Setup

If you want to modify these plugins or create new ones that depend on external libraries (like `numpy` or `scipy`), you need to set up a virtual environment (`.venv`) that Graph can use.

### 1. Creating the Virtual Environment (`.venv`)
Graph uses its own embedded Python 3.7 distribution. To ensure compatibility, you must create the virtual environment using **that specific Python executable**.

1.  Open a terminal (PowerShell or Command Prompt).
2.  Navigate to the `Plugins` directory:
    ```powershell
    cd "C:\_PROGRAMS\Graph\Plugins"
    ```
3.  Run the following command to create the virtual environment using Graph's Python:
    ```powershell
    # Adjust the path to Graph's Python executable if necessary
    & "..\Python\python.exe" -m venv .venv
    ```
4.  Activate the environment and install dependencies:
    ```powershell
    .\.venv\Scripts\Activate.ps1
    pip install numpy scipy
    ```

### 2. Using `setup_venv()` from `common`
To make your plugins work with this virtual environment, you must ensure that the `.venv` site-packages are added to `sys.path` before importing any external library.

The `common` module handles this automatically. You just need to import it at the beginning of your plugin:

```python
# Import common module (automatically configures .venv)
from common import setup_venv
# Now you can import external libraries safely
import numpy as np
from scipy.ndimage import gaussian_filter1d
```

The `setup_venv()` function in `common/__init__.py` locates the `.venv` directory relative to the `Plugins` folder and adds its `Lib/site-packages` to the Python path.

---

# 1. Filters

## 📉 Gaussian Filter
Applies a Gaussian smoothing filter to the selected point series. This is useful for reducing noise in experimental data while preserving the general trend.

**Parameters:**
*   **Sigma (σ)**: The standard deviation of the Gaussian kernel in units of the X-axis (Time). Controls the "width" of the smoothing.
    *   *Suggested*: ~1% of the X range.
*   **Mode**: Determines how the signal is extended at the boundaries (e.g., `nearest`, `reflect`, `mirror`).
*   **Truncate**: Limits the size of the kernel to a number of standard deviations (default is 4.0).
*   **Result**: Choose to create a **New Series** (preserving the original) or **Replace** the existing one.

![Gaussian Filter](screenshots/demo_gaussian_filter.png)

*Figure: Gaussian Filter applied to a noisy signal*

---

## 📊 Selective Median Filter
Applies a median filter to remove "salt and pepper" noise or outliers without blurring sharp edges as much as a linear filter.

**Parameters:**
*   **Window Size**: The number of points in the sliding window (must be an odd integer, e.g., 3, 5, 7).
*   **Threshold**: The deviation threshold. If the difference between a point and the median of its neighbors exceeds this value, the point is replaced by the median.
*   **Result**: Create a new series or replace the original.

![Selective Median Filter](screenshots/demo_selective_median_filter.png)

*Figure: Selective Median Filter removing spikes from a signal*

---

# 2. Importing

## 📂 Advanced CSV Importer
A flexible tool for importing data from CSV or text files, with automatic column detection and type parsing.

**Features & Parameters:**
*   **File Preview**: Shows the selected filename and data preview.
*   **Header**: Option to indicate if the first row contains column names.
*   **Separator**: Auto-detects or allows manual selection of delimiters (Comma, Semicolon, Tab, Pipe).
*   **X Column**: Select which column represents the X-axis (Time/Index). Other numeric columns become Y-series.
*   **Date/Time Parsing**: Automatically converts DateTime columns into relative seconds (t=0 at first sample).

![Advanced CSV Importer](screenshots/demo_advanced_csv_import.png)

*Figure: Advanced CSV Import Configuration Dialog*

---

## 📋 Profile Manager
Saves and loads axis and graph configuration profiles. Useful for quickly switching between different graph configurations.

**Features:**
*   **Save Profile**: Saves current axis limits, labels, fonts, and graph settings to a JSON file.
*   **Load Profile**: Restores a previously saved configuration.
*   **Delete Profile**: Removes saved profiles.
*   **Profile List**: Browse and manage all saved profiles.

![Profile Manager](screenshots/demo_profile_manager.png)

*Figure: Profile Manager Dialog*

---

# 3. Morphing

## 🔄 Morph - Transform Series
Transforms a point series to new X and Y limits. Useful for scaling and shifting data to match different coordinate systems.

**Parameters:**
*   **Current Limits**: Displays the current X and Y range of the selected series.
*   **New X Limits**: Target minimum and maximum X values.
*   **New Y Limits**: Target minimum and maximum Y values.
*   **Result**: Choose to create a **New Series** or **Replace** the original.

![Morph Transform](screenshots/demo_morphing.png)

*Figure: Morph dialog for transforming series limits*

---

## 📐 Resample
Resamples a point series using various interpolation methods. Useful for changing the sampling rate or regularizing irregularly sampled data.

**Parameters:**
*   **New Sampling Period**: The desired time interval between samples.
*   **Interpolation Method**: Choose from Linear (`np.interp`), `CubicSpline`, `PchipInterpolator`, or `Akima1DInterpolator`.
*   **Result**: Create a new series or replace the original.

![Resample](screenshots/demo_resample.png)

*Figure: Resample Dialog showing interpolation options*

---

## 📊 Signal Info
Calculates and displays statistical information about the selected point series, with optional visualization of statistics as horizontal lines on the graph.

**Statistics Displayed:**
*   **Y Range**: Minimum and Maximum Y values.
*   **Mean**: Average of Y values.
*   **Median**: Middle value of Y data.
*   **Standard Deviation**: Measure of data dispersion.
*   **Add Info Lines**: Optionally adds horizontal lines for Ymin, Ymax, Mean, Median, and ±1 std.

![Signal Info](screenshots/demo_signal_info.png)

*Figure: Signal Info dialog with statistical analysis*

---

## 🔢 Apply Function
Applies a custom mathematical function `f(y)` to each Y value of the selected point series, generating a new transformed series.

**Parameters:**
*   **Selected Series**: Displays the name and point count of the currently selected series.
*   **Function f(y)**: Enter a mathematical expression using `y` as the variable (e.g., `y^2`, `sqrt(y)`, `ln(y)`).
*   **Output Mode**: Choose to create a **New Series** or **Replace** the original.
*   **Series Color**: Select the color for the new series (when creating a new one).

**Examples:**
*   `y^2` - Square each Y value
*   `sqrt(y)` - Square root transformation
*   `abs(y)` - Absolute value
*   `ln(y)` - Natural logarithm
*   `10*y + 5` - Linear transformation
*   `sin(y)` - Sine of Y values
*   `e^(-y)` - Exponential decay

![Apply Function](screenshots/demo_apply_function.png)

*Figure: Apply Function dialog for transforming Y values*

---

## ➕ Linear Combination
Combines multiple point series linearly using the formula `y = Σ kᵢ · yᵢ(x)`, where each series is multiplied by a user-defined factor.

**Parameters:**
*   **Base Series**: The selected series defines the X domain (all other series are interpolated to these X values).
*   **Series List**: Shows all visible point series with:
    *   **Checkbox**: Select which series to include in the combination.
    *   **Factor (kᵢ)**: The multiplication factor for each series (default: 1.00).
    *   **Legend**: Series name (limited to 50 characters).
*   **Interpolation**: Uses CubicSpline with extrapolation for non-base series.
*   **Result Color**: Choose the color for the resulting combined series.

**Example:**
```
[✓]  [ 3.50 ]   sin(x)
[ ]  [ 1.00 ]   x + 3
[✓]  [-1.54 ]   x^2 + x
```
Result: `y = 3.5·sin(x) - 1.54·(x² + x)`

![Linear Combination](screenshots/demo_linear_combination.png)

*Figure: Linear Combination dialog for combining multiple series*

---

# 4. Visualization

## 🔲 Draw Visible Rect
Draws a rectangle that matches the current visible axis area. Useful for marking or highlighting the current view boundaries.

**Features:**
*   Automatically reads current X and Y axis limits.
*   Creates a dashed rectangle as a point series.

![Draw Visible Rect](screenshots/demo_visible_rect.png)

*Figure: Visible rectangle drawn on the graph area*

---

# 5. Waveform Generation (wfgen)

## 〰️ Composite Signal Generator
Generates a composite signal formed by the sum of up to six sinusoidal waves, with optional noise.

**Parameters:**
*   **Signals 1-6**: Configure **Frequency (Hz)**, **Amplitude (V)**, and **Phase (rad)** for each component.
*   **Sampling**:
    *   **Fs**: Sampling Frequency (Hz).
    *   **T0 / Tf**: Start and End time (seconds).
*   **Noise**: Amplitude of Gaussian noise added to the signal.
*   **Appearance**: Select **Color** and **Thickness** for the generated plot.

![Composite Signal Generator](screenshots/demo_composite_signal_generator.png)

*Figure: Composite Signal Generator Dialog*

---

## 🤖 AI Function Generator

Generates mathematical functions using **OpenAI's GPT models** with natural language prompts. Describe the function you want in plain English or Spanish, and the AI will generate the appropriate equation, interval, and legend for Graph. Now supports both **standard** (y = f(x)) and **parametric** (x(t), y(t)) functions, chosen automatically by the model.

**Features:**
*   **Natural Language Input**: Describe your function in everyday language (e.g., "A parabola that passes through the origin", "A circle of radius 5").
*   **Automatic Function Type**: The AI decides whether to generate a standard (y = f(x)) or parametric (x(t), y(t)) function based on your description.
*   **Model Selection**: Choose from multiple OpenAI models (GPT-4, GPT-5, o3, etc.) directly in the plugin dialog.
*   **Reasoning Level**: Select the reasoning effort (low, medium, high) for more accurate or creative results.
*   **Verbosity**: Control the level of explanation detail (low, medium, high).
*   **Structured Output**: Uses OpenAI's structured outputs with Pydantic validation to ensure correct Graph syntax.
*   **Automatic Interval**: The AI suggests an appropriate interval for x or t based on the function type.
*   **Session API Key**: If no API key is configured in `.env`, the plugin prompts for manual entry. The key is stored only for the current session.

**Configuration (`.env` file in Plugins folder):**
```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-5.1
```

**Usage:**
1.  Open the dialog from `Plugins → Graphîa → AWF Generators → AI Function Generator...`
2.  Enter a description of the function you want to create.
3.  Select the desired model, reasoning level, and verbosity.
4.  Click **Generate** to send the request to OpenAI.
5.  Review the generated equation(s), interval, and explanation.
6.  Click **Accept** to add the function to Graph.

**Function Types:**
*   **Standard**: y = f(x) (e.g., lines, parabolas, sine waves)
*   **Parametric**: x(t), y(t) (e.g., circles, ellipses, spirals, Lissajous curves)
  The plugin automatically chooses the type based on your prompt.

**Example Prompts:**
*   "A parabola that passes through the origin"
*   "Sine function between 0 and 2π"
*   "A circle of radius 5"
*   "Draw an ellipse with horizontal axis 6 and vertical axis 3"
*   "A spiral"
*   "Lissajous curve"
*   "A heart shape"

**Example Outputs:**
*   Standard: `y = x^2`, interval: -5 to 5
*   Parametric: `x(t) = 5*cos(t)`, `y(t) = 5*sin(t)`, interval: 0 to 2π

**Screenshots:**
![AI Function Generator - Standard](screenshots/demo_ai_standard.png)
*Figure: Standard function generated from natural language*

![AI Function Generator - Parametric](screenshots/demo_ai_parametric.png)
*Figure: Parametric function generated from natural language*

![AI Function Generator](screenshots/demo_ai1.png)
*Figure: AI Function Generator dialog with natural language input*

![AI Generated Function](screenshots/demo_ai2.png)
*Figure: Generated function displayed in Graph*

---

## ⚡ Spike Generator
Injects random "spikes" (outliers) into an existing signal. Excellent for testing the robustness of filters (like the Selective Median Filter).

**Parameters:**
*   **Proportion (%)**: Percentage of total points to be affected by spikes.
*   **Amplitude Range**: Minimum and Maximum amplitude for the generated spikes.
*   **Result**: Create a new series or replace the original.

![Spike Generator](screenshots/demo_spike_generator.png)

*Figure: Signal with generated spikes*

---

## 📢 Noise Generator
Adds random noise to the selected point series. Supports both Normal (Gaussian) and Uniform noise distributions.

**Parameters:**
*   **Noise Type**: Choose between **Normal** (Gaussian distribution) or **Uniform** distribution.
*   **Amplitude / Std Dev**: For Uniform noise, specifies the range; for Normal noise, specifies the standard deviation.
*   **Result**: Create a new series or replace the original.

![Noise Generator](screenshots/demo_noise_generator.png)

*Figure: Noise Generator Dialog*

![Uniform Noise Generator](screenshots/demo_uniform_noise_generator.png)

*Figure: Signal with uniform noise applied*

---

## � Function Sampler
Samples a selected mathematical function (TStdFunc) at discrete points to generate a point series. This is useful for converting continuous functions into discrete data for further processing or analysis.

**Parameters:**
*   **Selected Function**: Displays the equation and interval of the currently selected function.
*   **Sampling Period (Ts)**: The time interval between consecutive samples. Default is 1% of the function's interval range.
*   **Start Time (t₀)**: The starting point for sampling (defaults to function's `From` value).
*   **End Time (tf)**: The ending point for sampling (defaults to function's `To` value).
*   **Series Color**: Choose the color for the generated point series.

**Formula:**
The plugin generates points using: `yᵢ = f(xᵢ)` where `xᵢ = t₀ + i·Ts`

**Usage:**
1.  Select a function (TStdFunc) in the function panel.
2.  Open the dialog from `Plugins → Graphîa → AWF Generators → Function Sampler...`
3.  Adjust the sampling period and time range as needed.
4.  Click **Sample** to generate the point series.

![Function Sampler](screenshots/demo_function_sampler.png)

*Figure: Function Sampler dialog and sampled points from a damped oscillation*

---

## �🛠️ Utilities

*   **ShowConsole (F11)**: Toggles the Python interpreter window, allowing for advanced debugging and direct script execution within Graph.
*   **Plugin Manager**: Install, update, and manage plugins from the Graph interface.

---

## 👨‍💻 Author

**Ing. Marcelo A. Valdez**
*Electronic Engineer*
*Systems Engineer for Structural Testing & Embedded Software Developer*

📍 **Location**: Córdoba, Argentina
📧 **Email**: zedlavolecram@gmail.com
🏢 **Workplace**: Laboratorio de Adquisición de Datos - Ensayos Estructurales - FAdeA S.A. (Fábrica Argentina de Aviones)

---
*Developed for the enhancement of data acquisition and processing workflows.*

## 📄 License

This project is licensed under the **MIT License**.

```text
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```
