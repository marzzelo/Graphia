# Smoothing package
# This package contains smoothing filter plugins for Graph (Gaussian, Median, etc.)

# Protected imports - allows individual plugins to be disabled
try:
    from . import Gaussian
except ImportError:
    pass

try:
    from . import Median
except ImportError:
    pass
