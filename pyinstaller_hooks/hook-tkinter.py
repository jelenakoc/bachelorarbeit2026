def pre_find_module_path(hook_api):
    # Keep tkinter available for analysis. In this project, tkinter imports
    # correctly at runtime, but PyInstaller's default pre-find hook incorrectly
    # marks it as broken and excludes it from the build.
    return
