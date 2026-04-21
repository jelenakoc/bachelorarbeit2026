def pre_find_module_path(hook_api):
    # Do not exclude tkinter. In this project/environment, tkinter imports and
    # runs correctly, but PyInstaller's stock pre-find hook mis-detects it as
    # broken and clears the search path.
    return
