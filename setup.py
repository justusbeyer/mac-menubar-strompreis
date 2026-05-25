from setuptools import setup

APP = ["strompreis.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,   # must be False for menubar apps
    "iconfile": None,
    "plist": {
        "CFBundleName": "Strompreis",
        "CFBundleDisplayName": "Strompreis",
        "CFBundleIdentifier": "de.strompreis",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        # No dock icon, menubar only
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
    "packages": ["rumps", "requests", "urllib3", "certifi", "charset_normalizer", "idna"],
}

setup(
    app=APP,
    name="Strompreis",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
