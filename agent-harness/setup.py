from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-gemini-desktop",
    version="0.1.0",
    description="Agent-native CLI harness for Google Gemini Desktop",
    packages=find_namespace_packages(include=["cli_anything*"]),
    install_requires=[
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-gemini-desktop=cli_anything.gemini_desktop.gemini_cli:cli",
        ],
    },
    python_requires=">=3.10",
)
