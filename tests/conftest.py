"""Root conftest — ensure agent service is importable for all tests."""
import sys
import os

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_agent_dir = os.path.join(_project_root, "services", "agent")
if _agent_dir not in sys.path:
    sys.path.insert(0, _agent_dir)
