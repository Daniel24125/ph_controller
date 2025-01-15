from setuptools import setup, find_packages

setup(
    name="RPi ",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # List your project dependencies here
        # "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=22.0",
            "flake8>=4.0",
        ],
    },
    author="Daniel Madalena",
    author_email="danielmadalena@msn.com",
    description="A project for RPi for sensor connection",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Daniel24125/ph_controller",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: RPi Debian",
    ],
    python_requires=">=3.8",
)