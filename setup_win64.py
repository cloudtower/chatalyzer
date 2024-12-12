from distutils.core import setup
from cx_Freeze import setup, Executable

build_exe_options = {"packages": ["flask","urllib","sqlite3","html.parser","unicodedata","time","math","datetime","json"]}

setup(  name = "chatalyzer_flask_backend",
        version = "2.0",
        description = "Flask backend for Chatalyzer chat analyzation tool",
        options = {"build_exe": build_exe_options},
        executables = [Executable("server_flask.py")])
