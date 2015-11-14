from setuptools import setup

setup(
    name="fseventwatcher",
    version="0.0.1",
    py_modules=["fseventwatcher"],
    install_requires=["supervisor", "watchdog"],
    entry_points="[console_scripts]\nfseventwatcher = fseventwatcher:main"
)
