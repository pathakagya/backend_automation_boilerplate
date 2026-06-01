"""Repository-level pytest hooks and fixtures.

This re-exports the shared hooks/fixtures from src.conftest so pytest can
discover them when running tests under tests/.
"""

from src.conftest import *  
