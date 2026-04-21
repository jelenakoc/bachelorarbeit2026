from pathlib import Path
import sys


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent

        # In portable builds, Dashboard.exe and Tracker.exe live in their own
        # subfolders. Both apps should still share one common database in the
        # parent "Zeiterfassung" folder.
        if executable_dir.name in {"Dashboard", "Tracker"}:
            return executable_dir.parent

        return executable_dir

    return Path(__file__).resolve().parent.parent


def get_resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    return Path(__file__).resolve().parent.parent


APP_ROOT = get_app_root()
RESOURCE_ROOT = get_resource_root()


def get_resource_path(*parts: str) -> Path:
    return RESOURCE_ROOT.joinpath(*parts)
