"""
AIFunctionGenerator - Plugin to generate mathematical functions using AI
Uses the OpenAI API with Structured Outputs to interpret
natural language prompts and generate functions for Graph.
"""

import Graph
import vcl
import os
import sys

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
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

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
    import openai
    from pydantic import BaseModel
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# Structured output schema definition
if HAS_OPENAI:
    class FunctionDefinition(BaseModel):
        equation: str
        interval_from: float
        interval_to: float
        legend: str
        explanation: str


# System prompt with rules and examples for Graph
SYSTEM_PROMPT = """You are an expert mathematics assistant that generates functions for the Graph software (https://www.padowan.dk/).
Your task is to interpret the user's request and generate a valid mathematical function.

# GRAPH SYNTAX RULES:

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

# VALID EQUATION EXAMPLES:

Basic functions:
- Linear: 2x + 3
- Quadratic: x^2 - 4x + 3
- Cubic: x^3 - 2x^2 + x
- Polynomial: x^4 - 3x^2 + 1

Trigonometric functions:
- Sine: sin(x)
- Cosine: cos(x)
- Tangent: tan(x)
- Sine squared: sin(x)^2
- Composition: sin(2x)
- With phase: sin(x + pi/4)
- Combination: sin(x) + cos(2x)

Exponential and logarithmic functions:
- Exponential: e^x
- Exponential with coefficient: e^(2x)
- Decay: e^(-x)
- Gaussian: e^(-x^2)
- Natural logarithm: ln(x)
- Base-10 logarithm: log(x)

Rational functions:
- Hyperbola: 1/x
- Rational: (x^2 + 1)/(x - 2)
- Lorentzian: 1/(1 + x^2)

Composite functions:
- Damped sine: e^(-x/10)*sin(x)
- Modulated wave: sin(x)*cos(10x)
- Gaussian bell: e^(-x^2/2)/sqrt(2*pi)

# REQUEST AND RESPONSE EXAMPLES:

User: "A parabola that passes through the origin"
→ equation: "x^2", interval_from: -5, interval_to: 5, legend: "y = x²"

User: "Sine function between 0 and 2π"
→ equation: "sin(x)", interval_from: 0, interval_to: 6.283, legend: "y = sin(x)"

User: "Line with slope 2 passing through (0, 1)"
→ equation: "2x + 1", interval_from: -5, interval_to: 5, legend: "y = 2x + 1"

User: "Gaussian bell centered at 0"
→ equation: "e^(-x^2/2)", interval_from: -4, interval_to: 4, legend: "Gaussian"

# INSTRUCTIONS:

1. Interpret the user's natural language request
2. Generate the equation using correct Graph syntax
3. Choose an appropriate interval if not specified (generally -10 to 10 or 0 to 10)
4. Create a descriptive and concise legend
5. Provide a brief explanation of the generated function

ALWAYS respond in structured JSON format with these fields:
- equation: the equation in Graph syntax
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
        Form.Width = 520
        Form.Height = 480
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
        
        # Model information
        lbl_model = vcl.TLabel(Form)
        lbl_model.Parent = Form
        lbl_model.Caption = f"Model: {OPENAI_MODEL}"
        lbl_model.Left = 20
        lbl_model.Top = 35
        lbl_model.Font.Color = 0x666666
        
        # Prompt label
        lbl_prompt = vcl.TLabel(Form)
        lbl_prompt.Parent = Form
        lbl_prompt.Caption = "Describe the function you want to create:"
        lbl_prompt.Left = 20
        lbl_prompt.Top = 60
        
        # User prompt memo
        memo_prompt = vcl.TMemo(Form)
        memo_prompt.Parent = Form
        memo_prompt.Left = 20
        memo_prompt.Top = 80
        memo_prompt.Width = 470
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
            "• Line passing through points (1, 2) and (3, 6)"
        )
        lbl_examples.Left = 20
        lbl_examples.Top = 170
        lbl_examples.Font.Color = 0x888888
        
        # Result panel (initially hidden)
        pnl_result = vcl.TPanel(Form)
        pnl_result.Parent = Form
        pnl_result.Left = 20
        pnl_result.Top = 250
        pnl_result.Width = 470
        pnl_result.Height = 130
        pnl_result.BevelOuter = "bvLowered"
        pnl_result.Color = 0xFFFFF8
        pnl_result.Visible = False
        
        lbl_result = vcl.TLabel(Form)
        lbl_result.Parent = pnl_result
        lbl_result.Caption = ""
        lbl_result.Left = 10
        lbl_result.Top = 5
        lbl_result.Font.Name = "Consolas"
        lbl_result.AutoSize = True
        
        # Variable to store result
        result_data = [None]  # Using list to allow modification from closure
        
        # Buttons
        btn_generate = vcl.TButton(Form)
        btn_generate.Parent = Form
        btn_generate.Caption = "Generate"
        btn_generate.Left = 220
        btn_generate.Top = 400
        btn_generate.Width = 90
        btn_generate.Height = 30
        
        btn_accept = vcl.TButton(Form)
        btn_accept.Parent = Form
        btn_accept.Caption = "Accept"
        btn_accept.Left = 320
        btn_accept.Top = 400
        btn_accept.Width = 80
        btn_accept.Height = 30
        btn_accept.Enabled = False
        
        btn_close = vcl.TButton(Form)
        btn_close.Parent = Form
        btn_close.Caption = "Close"
        btn_close.ModalResult = 2
        btn_close.Cancel = True
        btn_close.Left = 410
        btn_close.Top = 400
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
            
            try:
                # Call OpenAI API using old syntax (v0.28.1)
                current_key = get_api_key()
                openai.api_key = current_key
                
                # Try with response_format if supported by API
                # If it fails, try without it
                try:
                    response = openai.ChatCompletion.create(
                        model=OPENAI_MODEL,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                    )
                except TypeError:
                    # If local library rejects the parameter, try without it
                    response = openai.ChatCompletion.create(
                        model=OPENAI_MODEL,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ]
                    )
                
                # Parse JSON response with Pydantic
                import json
                # In v0.28.1 response is a dict-like object
                content = response['choices'][0]['message']['content']
                json_response = json.loads(content)
                parsed = FunctionDefinition(**json_response)
                result_data[0] = parsed
                
                # Show result
                result_text = (
                    f"Equation:  {parsed.equation}\n"
                    f"Interval:  [{parsed.interval_from:.4g}, {parsed.interval_to:.4g}]\n"
                    f"Legend:    {parsed.legend}\n"
                    f"───────────────────────────────────\n"
                    f"{parsed.explanation}"
                )
                lbl_result.Caption = result_text
                pnl_result.Visible = True
                btn_accept.Enabled = True
                
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
                # Create the function in Graph
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
