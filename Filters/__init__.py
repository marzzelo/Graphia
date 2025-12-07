# Filters package
# This package contains filtering plugins for Graph

# Protected imports - allows individual plugins to be disabled
try:
    from . import Gaussian
except ImportError:
    pass

try:
    from . import Median
except ImportError:
    pass
