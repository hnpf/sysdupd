from setuptools import setup, find_packages

setup(
    name="sysdupd",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pygobject",
    ],
    entry_points={
        "console_scripts": [
            "sysdupd=sysdupd.__main__:main",
        ],
    },
    include_package_data=True,
)