# Filtering package
# This package contains frequency-domain filtering plugins for Graph (FIR, IIR, etc.)

# Protected imports - allows individual plugins to be disabled
try:
    from . import firwin
except ImportError:
    pass

# add convolution
try:
    from . import convolution
except ImportError:
    pass
