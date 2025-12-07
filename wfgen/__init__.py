# wfgen package
# This package contains signal generation plugins for Graph

# Protected imports - allows individual plugins to be disabled
try:
    from . import SinePointsGenerator
except ImportError:
    pass

try:
    from . import SpikeGenerator
except ImportError:
    pass

try:
    from . import NoiseGenerator
except ImportError:
    pass

try:
    from . import AIFunctionGenerator
except ImportError:
    pass

try:
    from . import FunctionSampler
except ImportError:
    pass
