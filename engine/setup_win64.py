import os
from distutils.core import setup
from cx_Freeze import setup, Executable

os.environ['TCL_LIBRARY'] = r'C:\Program Files\Python35\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Program Files\Python35\tcl\tk8.6'

build_exe_options = {"packages": ["flask","urllib","sqlite3","html.parser","unicodedata","time","math","datetime","json"]}

setup(  name = "chatalyzer_flask_backend",
        version = "0.1",
        description = "Flask backend for Chatalyzer chat analyzation tool",
        options = {"build_exe": build_exe_options},
        executables = [Executable("server_flask.py")])
