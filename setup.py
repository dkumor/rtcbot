import pathlib
import setuptools

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setuptools.setup(
    name="rtcbot",
    version="0.0.7",
    description="An asyncio-focused library for webrtc robot control",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/dkumor/rtcbot",
    author="Daniel Kumor",
    author_email="daniel@dkumor.com",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
    ],
    packages=setuptools.find_packages(),
    include_package_data=True,
    python_requires=">=3.5.0",
    install_requires=[
        "aiortc",
        "pyserial",
        "pyserial-asyncio",
        "numpy",
        "aiohttp",
        "soundcard",
        "inputs",
        "pynmea2",
    ],
)
