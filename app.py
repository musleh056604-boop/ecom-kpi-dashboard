from __future__ import annotations

from pathlib import Path
from runpy import run_path


# Streamlit Cloud remains configured for app.py; this public entrypoint runs only the service page.
SERVICE_ENTRYPOINT = Path(__file__).with_name("service_app.py")
run_path(str(SERVICE_ENTRYPOINT))
