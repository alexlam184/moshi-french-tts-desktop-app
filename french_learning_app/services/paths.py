import os
from pathlib import Path


def app_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / "Library" / "Application Support"
    path = base / "FrenchLearningApp"
    path.mkdir(parents=True, exist_ok=True)
    return path
