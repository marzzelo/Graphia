# morphing/__init__.py
# Package for waveform manipulation and analysis tools

# Protected imports - allows individual plugins to be disabled
try:
    from . import signal_info
except ImportError:
    pass

try:
    from . import resample
except ImportError:
    pass

try:
    from . import morph
except ImportError:
    pass

try:
    from . import apply_function
except ImportError:
    pass

try:
    from . import linear_combination
except ImportError:
    pass

try:
    from . import crop
except ImportError:
    pass

try:
    from . import spectral_interpolation
except ImportError:
    pass

try:
    from . import fill_segment
except ImportError:
    pass