import os
from setuptools import setup, find_packages

setup(
    name="pulsewatch",
    version="0.1.0",
    description="Lightweight Python telemetry client for PulseWatch observability",
    long_description=open("README.md", "r", encoding="utf-8").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="PulseWatch Team",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
