"""
AIFunctionGenerator - Plugin to generate mathematical functions using AI
Uses the OpenAI Responses API with GPT-5.1 to interpret
natural language prompts and generate functions for Graph.
"""

import Graph
import vcl
import os
import sys
import json

# Import common utilities (configures venv automatically)
from common import setup_venv, show_error, show_info

# Ensure venv is configured before importing external packages
setup_venv()

# Now we can import packages from venv
from dotenv import load_dotenv

# Load .env from the Plugins folder
plugins_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.join(plugins_dir, '.env')
load_dotenv(env_path)

# Get configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-5.1')

# Available models for selection (reasoning models only)
AVAILABLE_MODELS = [
    "gpt-5.1",
    "gpt-5.1-mini",
    "gpt-5",
    "o3",
    "o3-mini",
    "o4-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
]

# Reasoning effort options
REASONING_EFFORTS = ["low", "medium", "high"]

# Verbosity options
VERBOSITY_OPTIONS = ["low", "medium", "high"]

# Session API key (used when user enters key manually)
_session_api_key = None
# Flag to mark when the .env key has failed authentication
_env_key_invalid = False

def get_api_key():
    """Returns the API key from environment or session."""
    global _session_api_key, _env_key_invalid
    if _session_api_key:
        return _session_api_key
    # Only return env key if it hasn't failed authentication
    if not _env_key_invalid and OPENAI_API_KEY and OPENAI_API_KEY != 'your-api-key-here':
        return OPENAI_API_KEY
    return None

def set_session_api_key(key):
    """Sets the API key for the current session."""
    global _session_api_key
    _session_api_key = key

def mark_env_key_invalid():
    """Marks the .env API key as invalid (failed authentication)."""
    global _env_key_invalid
    _env_key_invalid = True

# Import OpenAI and Pydantic
try:
    from openai import OpenAI
    from pydantic import BaseModel
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# Structured output schema definition
if HAS_OPENAI:
    from typing import Optional
    
    class FunctionDefinition(BaseModel):
        # Function type: "standard" for y=f(x), "parametric" for x(t), y(t)
        function_type: str  # "standard" or "parametric"
        
        # For standard functions: y = f(x)
        equation: Optional[str] = None
        
        # For parametric functions: x(t), y(t)
        x_equation: Optional[str] = None
        y_equation: Optional[str] = None
        
        # Interval for the independent variable (x for standard, t for parametric)
        interval_from: float
        interval_to: float
        
        legend: str
        explanation: str
    
    # Generate JSON schema (compatible with Pydantic v1 and v2)
    def get_function_schema():
        """Returns the JSON schema for FunctionDefinition, compatible with Pydantic v1 and v2."""
        if hasattr(FunctionDefinition, 'model_json_schema'):
            # Pydantic v2
            return FunctionDefinition.model_json_schema()
        else:
            # Pydantic v1
            return FunctionDefinition.schema()


# System prompt with rules and examples for Graph
SYSTEM_PROMPT = """You are an expert mathematics assistant that generates functions for the Graph software (https://www.padowan.dk/).
Your task is to interpret the user's request and generate a valid mathematical function.

You can generate TWO types of functions:
1. STANDARD functions: y = f(x) - use when the function can be expressed as y in terms of x
2. PARAMETRIC functions: x(t), y(t) - use for curves that cannot be expressed as y=f(x), like circles, spirals, Lissajous figures, cycloids, etc.

# GRAPH SYNTAX RULES:

## For STANDARD functions (y = f(x)):
1. The independent variable MUST always be 'x' (lowercase)
2. Implicit multiplication is allowed: 2x means 2*x
3. Exponents use the ^ symbol: x^2 means x²
4. Trigonometric functions use radians
5. The number pi is written as 'pi'
6. Euler's number e is written as 'e'
7. Square root is sqrt(x)
8. Absolute value is abs(x)
9. Natural logarithm is ln(x), base-10 logarithm is log(x)
10. For exponential: e^x or exp(x)

## For PARAMETRIC functions (x(t), y(t)):
1. The parameter MUST always be 't' (lowercase)
2. Same syntax rules apply for operators and functions
3. Both x(t) and y(t) must be provided
4. The interval is for the parameter t

# STANDARD FUNCTION EXAMPLES:

Basic functions:
- Linear: 2x + 3
- Quadratic: x^2 - 4x + 3
- Cubic: x^3 - 2x^2 + x
- Polynomial: x^4 - 3x^2 + 1

Trigonometric functions:
- Sine: sin(x)
- Cosine: cos(x)
- With phase: sin(x + pi/4)
- Combination: sin(x) + cos(2x)

Exponential and logarithmic functions:
- Exponential: e^x
- Gaussian: e^(-x^2)
- Natural logarithm: ln(x)

Rational functions:
- Hyperbola: 1/x
- Lorentzian: 1/(1 + x^2)

Composite functions:
- Damped sine: e^(-x/10)*sin(x)
- Gaussian bell: e^(-x^2/2)/sqrt(2*pi)

# PARAMETRIC FUNCTION EXAMPLES:

Circle (radius R=3, centered at origin):
- x(t) = 3*cos(t)
- y(t) = 3*sin(t)
- t from 0 to 2*pi

Ellipse (semi-axes a=4, b=2):
- x(t) = 4*cos(t)
- y(t) = 2*sin(t)
- t from 0 to 2*pi

Spiral (Archimedean):
- x(t) = t*cos(t)
- y(t) = t*sin(t)
- t from 0 to 6*pi

Logarithmic spiral:
- x(t) = e^(0.1*t)*cos(t)
- y(t) = e^(0.1*t)*sin(t)
- t from 0 to 4*pi

Lissajous figure (3:2 ratio):
- x(t) = sin(3*t)
- y(t) = sin(2*t)
- t from 0 to 2*pi

Cycloid:
- x(t) = t - sin(t)
- y(t) = 1 - cos(t)
- t from 0 to 4*pi

Epicycloid:
- x(t) = 5*cos(t) - cos(5*t)
- y(t) = 5*sin(t) - sin(5*t)
- t from 0 to 2*pi

Hypocycloid (astroid):
- x(t) = 3*cos(t) + cos(3*t)
- y(t) = 3*sin(t) - sin(3*t)
- t from 0 to 2*pi

Heart curve:
- x(t) = 16*sin(t)^3
- y(t) = 13*cos(t) - 5*cos(2*t) - 2*cos(3*t) - cos(4*t)
- t from 0 to 2*pi

Butterfly curve:
- x(t) = sin(t)*(e^cos(t) - 2*cos(4*t) - sin(t/12)^5)
- y(t) = cos(t)*(e^cos(t) - 2*cos(4*t) - sin(t/12)^5)
- t from 0 to 12*pi

# REQUEST AND RESPONSE EXAMPLES:

User: "A parabola that passes through the origin"
→ function_type: "standard", equation: "x^2", interval_from: -5, interval_to: 5

User: "Sine function between 0 and 2π"
→ function_type: "standard", equation: "sin(x)", interval_from: 0, interval_to: 6.283

User: "A circle of radius 5"
→ function_type: "parametric", x_equation: "5*cos(t)", y_equation: "5*sin(t)", interval_from: 0, interval_to: 6.283

User: "Draw an ellipse with horizontal axis 6 and vertical axis 3"
→ function_type: "parametric", x_equation: "6*cos(t)", y_equation: "3*sin(t)", interval_from: 0, interval_to: 6.283

User: "A spiral"
→ function_type: "parametric", x_equation: "t*cos(t)", y_equation: "t*sin(t)", interval_from: 0, interval_to: 18.85

User: "Lissajous curve"
→ function_type: "parametric", x_equation: "sin(3*t)", y_equation: "sin(2*t)", interval_from: 0, interval_to: 6.283

User: "A heart shape"
→ function_type: "parametric", x_equation: "16*sin(t)^3", y_equation: "13*cos(t) - 5*cos(2*t) - 2*cos(3*t) - cos(4*t)", interval_from: 0, interval_to: 6.283

# DECISION CRITERIA:

Use PARAMETRIC when:
- The curve is closed (circles, ellipses, hearts)
- The curve loops or spirals
- It cannot be expressed as a single y=f(x) (like a full circle)
- User mentions: circle, ellipse, spiral, cycloid, Lissajous, heart, butterfly, rose, cardioid, epicycloid, hypocycloid

Use STANDARD for everything else (parabolas, lines, waves, exponentials, etc.)

# INSTRUCTIONS:

1. Interpret the user's natural language request
2. Decide if the function should be STANDARD or PARAMETRIC
3. Generate the equation(s) using correct Graph syntax
4. Choose an appropriate interval if not specified
5. Create a descriptive and concise legend
6. Provide a brief explanation of the generated function

ALWAYS respond in structured JSON format with these fields:
- function_type: "standard" or "parametric"
- equation: the equation for standard functions (null for parametric)
- x_equation: x(t) for parametric functions (null for standard)
- y_equation: y(t) for parametric functions (null for standard)
- interval_from: start of interval (number)
- interval_to: end of interval (number)
- legend: legend text
- explanation: brief explanation of the function
"""


def request_api_key_dialog():
    """
    Shows a dialog to request the OpenAI API key from the user.
    Returns the API key if entered, None if cancelled.
    """
    Form = vcl.TForm(None)
    result = [None]
    
    try:
        Form.Caption = "OpenAI API Key Required"
        Form.Width = 500
        Form.Height = 280
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        # Warning icon and message
        lbl_warning = vcl.TLabel(Form)
        lbl_warning.Parent = Form
        lbl_warning.Caption = "⚠️ OpenAI API Key not found"
        lbl_warning.Left = 20
        lbl_warning.Top = 15
        lbl_warning.Font.Style = {"fsBold"}
        lbl_warning.Font.Size = 10
        
        # Instructions
        lbl_info = vcl.TLabel(Form)
        lbl_info.Parent = Form
        lbl_info.Caption = (
            "Please enter your OpenAI API key below.\n"
            "The key will be valid until Graph is closed.\n\n"
            "To avoid entering the key each time, create a .env file\n"
            "in the Plugins folder with the following content:\n"
            "OPENAI_API_KEY=your-api-key-here"
        )
        lbl_info.Left = 20
        lbl_info.Top = 45
        lbl_info.Font.Color = 0x444444
        
        # API Key label
        lbl_key = vcl.TLabel(Form)
        lbl_key.Parent = Form
        lbl_key.Caption = "API Key:"
        lbl_key.Left = 20
        lbl_key.Top = 155
        
        # API Key input
        edt_key = vcl.TEdit(Form)
        edt_key.Parent = Form
        edt_key.Left = 80
        edt_key.Top = 152
        edt_key.Width = 390
        edt_key.PasswordChar = '•'
        edt_key.Text = ""
        
        # Buttons
        btn_ok = vcl.TButton(Form)
        btn_ok.Parent = Form
        btn_ok.Caption = "OK"
        btn_ok.Left = 300
        btn_ok.Top = 200
        btn_ok.Width = 80
        btn_ok.Height = 28
        
        btn_cancel = vcl.TButton(Form)
        btn_cancel.Parent = Form
        btn_cancel.Caption = "Cancel"
        btn_cancel.Left = 390
        btn_cancel.Top = 200
        btn_cancel.Width = 80
        btn_cancel.Height = 28
        btn_cancel.ModalResult = 2
        btn_cancel.Cancel = True
        
        def on_ok_click(Sender):
            key = edt_key.Text.strip()
            if key and key.startswith('sk-'):
                result[0] = key
                Form.ModalResult = 1
            else:
                show_error(
                    "Please enter a valid OpenAI API key.\n"
                    "It should start with 'sk-'.",
                    "Invalid API Key"
                )
        
        btn_ok.OnClick = on_ok_click
        
        if Form.ShowModal() == 1:
            return result[0]
        return None
        
    finally:
        Form.Free()


def generate_function_dialog(Action):
    """
    Shows a dialog to generate functions using AI.
    """
    if not HAS_OPENAI:
        show_error(
            "The 'openai' module is not installed.\n\n"
            "Run in a terminal:\n"
            "pip install openai pydantic python-dotenv",
            "AI Function Generator"
        )
        return
    
    # Check for API key, request if not available
    api_key = get_api_key()
    if not api_key:
        api_key = request_api_key_dialog()
        if not api_key:
            return  # User cancelled
        set_session_api_key(api_key)

    # Create main form
    Form = vcl.TForm(None)
    try:
        Form.Caption = "AI Function Generator"
        Form.Width = 550
        Form.Height = 580
        Form.Position = "poScreenCenter"
        Form.BorderStyle = "bsDialog"
        
        # Icon in top-right corner
        icon_path = os.path.join(os.path.dirname(__file__), "AIFunctionGenerator_sm.png")
        if os.path.exists(icon_path):
            img_icon = vcl.TImage(Form)
            img_icon.Parent = Form
            img_icon.Left = Form.ClientWidth - 74
            img_icon.Top = 10
            img_icon.Width = 64
            img_icon.Height = 64
            img_icon.Stretch = True
            img_icon.Picture.LoadFromFile(icon_path)
        
        # Title
        lbl_title = vcl.TLabel(Form)
        lbl_title.Parent = Form
        lbl_title.Caption = "Generate mathematical functions with AI"
        lbl_title.Left = 20
        lbl_title.Top = 15
        lbl_title.Font.Style = {"fsBold"}
        
        # Model selection
        lbl_model = vcl.TLabel(Form)
        lbl_model.Parent = Form
        lbl_model.Caption = "Model:"
        lbl_model.Left = 20
        lbl_model.Top = 42
        
        cb_model = vcl.TComboBox(Form)
        cb_model.Parent = Form
        cb_model.Left = 70
        cb_model.Top = 39
        cb_model.Width = 120
        cb_model.Style = "csDropDownList"
        for model in AVAILABLE_MODELS:
            cb_model.Items.Add(model)
        # Set default model
        default_idx = 0
        for i, m in enumerate(AVAILABLE_MODELS):
            if m == OPENAI_MODEL:
                default_idx = i
                break
        cb_model.ItemIndex = default_idx
        
        # Reasoning effort
        lbl_reasoning = vcl.TLabel(Form)
        lbl_reasoning.Parent = Form
        lbl_reasoning.Caption = "Reasoning:"
        lbl_reasoning.Left = 200
        lbl_reasoning.Top = 42
        
        cb_reasoning = vcl.TComboBox(Form)
        cb_reasoning.Parent = Form
        cb_reasoning.Left = 270
        cb_reasoning.Top = 39
        cb_reasoning.Width = 80
        cb_reasoning.Style = "csDropDownList"
        for effort in REASONING_EFFORTS:
            cb_reasoning.Items.Add(effort)
        cb_reasoning.ItemIndex = 1  # medium by default for better accuracy
        
        # Verbosity
        lbl_verbosity = vcl.TLabel(Form)
        lbl_verbosity.Parent = Form
        lbl_verbosity.Caption = "Verbosity:"
        lbl_verbosity.Left = 360
        lbl_verbosity.Top = 42
        
        cb_verbosity = vcl.TComboBox(Form)
        cb_verbosity.Parent = Form
        cb_verbosity.Left = 420
        cb_verbosity.Top = 39
        cb_verbosity.Width = 80
        cb_verbosity.Style = "csDropDownList"
        for verb in VERBOSITY_OPTIONS:
            cb_verbosity.Items.Add(verb)
        cb_verbosity.ItemIndex = 1  # medium by default
        
        # Separator
        sep1 = vcl.TBevel(Form)
        sep1.Parent = Form
        sep1.Left = 10
        sep1.Top = 70
        sep1.Width = 520
        sep1.Height = 2
        sep1.Shape = "bsTopLine"
        
        # Prompt label
        lbl_prompt = vcl.TLabel(Form)
        lbl_prompt.Parent = Form
        lbl_prompt.Caption = "Describe the function you want to create:"
        lbl_prompt.Left = 20
        lbl_prompt.Top = 80
        
        # User prompt memo
        memo_prompt = vcl.TMemo(Form)
        memo_prompt.Parent = Form
        memo_prompt.Left = 20
        memo_prompt.Top = 100
        memo_prompt.Width = 500
        memo_prompt.Height = 80
        memo_prompt.ScrollBars = "ssVertical"
        memo_prompt.Text = ""
        
        # Examples
        lbl_examples = vcl.TLabel(Form)
        lbl_examples.Parent = Form
        lbl_examples.Caption = (
            "Examples:\n"
            "• A parabola passing through the origin with vertex at (0, -4)\n"
            "• Sine function with amplitude 2 and period π\n"
            "• A circle of radius 5 centered at the origin\n"
            "• An ellipse, a spiral, a Lissajous curve, a heart shape..."
        )
        lbl_examples.Left = 20
        lbl_examples.Top = 190
        lbl_examples.Font.Color = 0x888888
        
        # Result panel (initially hidden)
        pnl_result = vcl.TPanel(Form)
        pnl_result.Parent = Form
        pnl_result.Left = 20
        pnl_result.Top = 280
        pnl_result.Width = 500
        pnl_result.Height = 150
        pnl_result.BevelOuter = "bvLowered"
        pnl_result.Color = 0xFFFFF8
        pnl_result.Visible = False
        
        # Use TMemo for word-wrap support
        memo_result = vcl.TMemo(pnl_result)
        memo_result.Parent = pnl_result
        memo_result.Left = 5
        memo_result.Top = 5
        memo_result.Width = 490
        memo_result.Height = 140
        memo_result.ReadOnly = True
        memo_result.BorderStyle = "bsNone"
        memo_result.Color = 0xFFFFF8
        memo_result.Font.Name = "Consolas"
        memo_result.Font.Size = 9
        memo_result.WordWrap = True
        memo_result.ScrollBars = "ssVertical"
        
        # Usage info label (token counts)
        lbl_usage = vcl.TLabel(Form)
        lbl_usage.Parent = Form
        lbl_usage.Caption = ""
        lbl_usage.Left = 20
        lbl_usage.Top = 440
        lbl_usage.Font.Color = 0x888888
        lbl_usage.Font.Size = 8
        
        # Variable to store result
        result_data = [None]  # Using list to allow modification from closure
        
        # Buttons
        btn_generate = vcl.TButton(Form)
        btn_generate.Parent = Form
        btn_generate.Caption = "Generate"
        btn_generate.Left = 240
        btn_generate.Top = 500
        btn_generate.Width = 90
        btn_generate.Height = 30
        
        btn_accept = vcl.TButton(Form)
        btn_accept.Parent = Form
        btn_accept.Caption = "Accept"
        btn_accept.Left = 340
        btn_accept.Top = 500
        btn_accept.Width = 80
        btn_accept.Height = 30
        btn_accept.Enabled = False
        
        btn_close = vcl.TButton(Form)
        btn_close.Parent = Form
        btn_close.Caption = "Close"
        btn_close.ModalResult = 2
        btn_close.Cancel = True
        btn_close.Left = 430
        btn_close.Top = 500
        btn_close.Width = 80
        btn_close.Height = 30
        
        def on_generate_click(Sender):
            user_prompt = memo_prompt.Text.strip()
            
            if not user_prompt:
                show_error("Please enter a function description.", "AI Function Generator")
                return
            
            # Disable button while processing
            btn_generate.Enabled = False
            btn_generate.Caption = "Generating..."
            Form.Cursor = -11  # crHourGlass
            lbl_usage.Caption = ""
            
            try:
                # Get current settings
                current_key = get_api_key()
                selected_model = AVAILABLE_MODELS[cb_model.ItemIndex]
                reasoning_effort = REASONING_EFFORTS[cb_reasoning.ItemIndex]
                verbosity = VERBOSITY_OPTIONS[cb_verbosity.ItemIndex]
                
                # Create OpenAI client
                client = OpenAI(api_key=current_key)
                
                # Check if Responses API is available (openai >= 1.40)
                has_responses_api = hasattr(client, 'responses')
                
                if has_responses_api:
                    # Use new Responses API
                    request_params = {
                        "model": selected_model,
                        "input": user_prompt,
                        "instructions": SYSTEM_PROMPT,
                        "text": {
                            "format": {
                                "type": "json_schema",
                                "name": "function_definition",
                                "schema": get_function_schema(),
                                "strict": True
                            },
                        },
                        "store": False,
                    }
                    
                    # Add reasoning config for GPT-5 models
                    if selected_model.startswith("gpt-5"):
                        request_params["reasoning"] = {"effort": reasoning_effort}
                    
                    response = client.responses.create(**request_params)
                    
                    # Extract output text
                    output_text = None
                    for item in response.output:
                        if item.type == "message":
                            for content in item.content:
                                if content.type == "output_text":
                                    output_text = content.text
                                    break
                    
                    if not output_text:
                        raise ValueError("No output text received from API")
                    
                    # Get usage info
                    usage_info = None
                    if response.usage:
                        usage_info = {
                            "input": response.usage.input_tokens,
                            "output": response.usage.output_tokens,
                            "total": response.usage.total_tokens
                        }
                else:
                    # Fallback to Chat Completions API
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ]
                    
                    # Build request params
                    chat_params = {
                        "model": selected_model,
                        "messages": messages,
                        "response_format": {"type": "json_object"},
                    }
                    
                    # Add reasoning_effort and verbosity via extra_body (works with older openai versions)
                    # These are supported by gpt-5.1, gpt-5, and o-series models
                    extra_params = {}
                    if selected_model.startswith("gpt-5") or selected_model.startswith("o"):
                        extra_params["reasoning_effort"] = reasoning_effort
                    extra_params["verbosity"] = verbosity
                    
                    if extra_params:
                        chat_params["extra_body"] = extra_params
                    
                    response = client.chat.completions.create(**chat_params)
                    
                    output_text = response.choices[0].message.content
                    
                    # Get usage info
                    usage_info = None
                    if response.usage:
                        usage_info = {
                            "input": response.usage.prompt_tokens,
                            "output": response.usage.completion_tokens,
                            "total": response.usage.total_tokens
                        }
                
                # Parse JSON response
                json_response = json.loads(output_text)
                parsed = FunctionDefinition(**json_response)
                result_data[0] = parsed
                
                # Show result based on function type
                if parsed.function_type == "parametric":
                    result_text = (
                        f"Type:      Parametric\n"
                        f"x(t) =     {parsed.x_equation}\n"
                        f"y(t) =     {parsed.y_equation}\n"
                        f"t ∈        [{parsed.interval_from:.4g}, {parsed.interval_to:.4g}]\n"
                        f"Legend:    {parsed.legend}\n"
                        f"{'─' * 50}\n"
                        f"{parsed.explanation}"
                    )
                else:
                    result_text = (
                        f"Type:      Standard\n"
                        f"y =        {parsed.equation}\n"
                        f"x ∈        [{parsed.interval_from:.4g}, {parsed.interval_to:.4g}]\n"
                        f"Legend:    {parsed.legend}\n"
                        f"{'─' * 50}\n"
                        f"{parsed.explanation}"
                    )
                memo_result.Text = result_text
                pnl_result.Visible = True
                btn_accept.Enabled = True
                
                # Show usage info
                if usage_info:
                    lbl_usage.Caption = (
                        f"Tokens: {usage_info['input']} in / {usage_info['output']} out "
                        f"(total: {usage_info['total']})"
                    )
                
            except Exception as e:
                error_msg = str(e)
                if "api_key" in error_msg.lower() or "authentication" in error_msg.lower() or "incorrect" in error_msg.lower():
                    show_error("Authentication error. Please verify your API key.", "AI Function Generator")
                    # Clear session key and mark env key as invalid
                    set_session_api_key(None)
                    mark_env_key_invalid()
                    # Request new API key immediately
                    new_key = request_api_key_dialog()
                    if new_key:
                        set_session_api_key(new_key)
                        # User can try again with the new key
                    else:
                        # User cancelled, close the dialog
                        Form.ModalResult = 2  # mrCancel
                else:
                    show_error(f"Error generating function:\n{error_msg}", "AI Function Generator")
                result_data[0] = None
                btn_accept.Enabled = False
                
            finally:
                btn_generate.Enabled = True
                btn_generate.Caption = "Generate"
                Form.Cursor = 0  # crDefault
        
        def on_accept_click(Sender):
            if result_data[0] is None:
                return
            
            parsed = result_data[0]
            
            try:
                if parsed.function_type == "parametric":
                    # Create parametric function in Graph
                    # TParFunc takes x(t) and y(t) as constructor arguments
                    func = Graph.TParFunc(parsed.x_equation, parsed.y_equation)
                    func.From = parsed.interval_from
                    func.To = parsed.interval_to
                    func.LegendText = parsed.legend
                else:
                    # Create standard function in Graph
                    func = Graph.TStdFunc(parsed.equation)
                    func.From = parsed.interval_from
                    func.To = parsed.interval_to
                    func.LegendText = parsed.legend
                
                # Add to graph
                Graph.FunctionList.append(func)
                Graph.Redraw()
                
                # Clear for new generation
                result_data[0] = None
                pnl_result.Visible = False
                btn_accept.Enabled = False
                memo_prompt.Text = ""
                
                # Close dialog
                Form.ModalResult = 1  # mrOk
                
            except Exception as e:
                show_error(f"Error creating function:\n{str(e)}", "AI Function Generator")
        
        btn_generate.OnClick = on_generate_click
        btn_accept.OnClick = on_accept_click
        
        Form.ShowModal()
    
    finally:
        Form.Free()


# Register action
Action = Graph.CreateAction(
    Caption="AI Function Generator...", 
    OnExecute=generate_function_dialog, 
    Hint="Generate mathematical functions using artificial intelligence (OpenAI)",
    IconFile=os.path.join(os.path.dirname(__file__), "AIFunctionGenerator_sm.png")
)

# Add to Plugins menu -> AWF Generators
Graph.AddActionToMainMenu(Action, TopMenu="Plugins", SubMenus=["Graphîa", "AWF Generators"])
