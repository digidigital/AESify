import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
# build_exe_options = {"packages": ["os"], "excludes": ["tkinter"]}

# GUI applications require a different base on Windows (the default is for
# a console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

includefiles = [('.\locale\de\LC_MESSAGES\AESify.mo','.\locale\de\LC_MESSAGES\AESify.mo')]

option = {
    "build_exe": {
        "include_msvcr": [],
        'include_files':includefiles     
    } 
}



setup(  name = "AESify",
        version = "1.5.1",
        description = "AESify - Encrypt PDF-Files Easily",
        options = option ,
        #executables = [Executable("AESify.py", base=base)])
        executables = [Executable("AESify.py", icon=".\\shield.ico", target_name="AESify.exe", base=base)])