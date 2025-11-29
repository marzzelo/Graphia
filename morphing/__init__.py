# morphing/__init__.py
# Package for waveform manipulation and analysis tools

# Importar sub-plugins para que se registren al cargar este paquete
from . import signal_info
from . import resample
from . import morph
from . import apply_function
from . import linear_combination
