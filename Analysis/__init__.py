# Analysis package
# This package contains signal analysis plugins for Graph

# Protected imports - allows individual plugins to be disabled
try:
    from . import AbsRelErrors
except ImportError:
    pass

try:
    from . import Histogram
except ImportError:
    pass

try:
    from . import fft
except ImportError:
    pass

try:
    from . import welch
except ImportError:
    pass

try:
    from . import ifft
except ImportError:
    pass
