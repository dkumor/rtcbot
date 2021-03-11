Installing RTCBot
=====================

RTCBot uses some very powerful libraries that have not yet made it to the standard repositories.
This can make it a bit difficult to install on some systems.

It is recommended that you first install it and try the examples on a Raspberry Pi or Ubuntu machine,
since there might still be some bugs on other operating systems.


Raspbian
++++++++++++++

RTCBot requires several dependencies which are best installed using apt-get::

    sudo apt-get install python3-numpy python3-cffi python3-aiohttp \
        libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
        libswscale-dev libswresample-dev libavfilter-dev libopus-dev \
        libvpx-dev pkg-config libsrtp2-dev python3-opencv pulseaudio

Then, you can complete the installation with pip::

    sudo pip3 install rtcbot

.. warning::
    You might need to reboot your Pi for RTCBot to work! If RTCBot freezes when starting microphone or speaker, it means that you need to start PulseAudio.

.. note::
    It is recommended that you use the Pi 4 with RTCBot. While it was tested to work down to the Raspberry Pi 3B, it was observed to have
    extra latency, since the CPU had difficulty keeping up with encoding the video stream while processing controller input.
    This is because RTCBot currently cannot take advantage of the Pi's hardware acceleration, 
    meaning that all video encoding is done in software.

.. note::
    These instructions were made with reference to Raspbian Buster.
    While the library *does* work on Raspbian Stretch,
    you'll need to install aiohttp through pip, and avoid installing opencv.

Ubuntu
+++++++++++

RTCbot requires several dependencies which are best installed using apt-get::

    sudo apt-get install python3-numpy python3-cffi python3-aiohttp \
        libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
        libswscale-dev libswresample-dev libavfilter-dev libopus-dev \
        libvpx-dev pkg-config libsrtp2-dev python3-opencv pulseaudio

Then, you can complete the installation with pip::

    sudo pip3 install rtcbot

.. warning::
    You might need to reboot, or manually start PulseAudio if it was not previously installed. If RTCBot freezes when starting microphone or speaker, it means that PulseAudio is not running.

Mac
+++++++++++

To install on Mac, you will want a modern python 3 (either through `MiniConda <https://docs.conda.io/en/latest/miniconda.html>`_ or Homebrew),
and have Xcode's development tools installed. Then, you can run::

    brew install ffmpeg opus libvpx pkg-config
    conda install opencv
    pip install rtcbot

.. note::
    If you have trouble installing OpenCV, you can skip it, or create a new conda environment.

Windows
+++++++++++

Installing on Windows is pretty involved, since you need to manually compile one of the required Python libraries.
Nevertheless, if you enjoy a challenge, you can start with setting up `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_, after which you can install the basic requirements::

    conda install aiohttp cffi numpy
    conda install -c conda-forge av opencv

.. note::
    If you have trouble installing OpenCV, you can skip it, or create a new conda environment.

The library that enables RTCBot to use WebRTC, aiortc, must be compiled from scratch, since no builds are available. 
To do so, you'll need the `Visual Studio C++ Build Tools <https://visualstudio.microsoft.com/downloads/>`_, and follow these steps:

1. Download and extract the latest `aiortc source code <https://github.com/aiortc/aiortc/releases>`_
2. Download and extract the `msvc15 build of libopus <https://github.com/ShiftMediaProject/opus/releases>`_ into the aiortc folder, so that its lib and include directories are right by setup.py
3. Download and extract the `msvc15 build of libvpx <https://github.com/ShiftMediaProject/libvpx/releases>`_ same as libopus (the include and lib folders should merge while extracting)
4. Build the extension::

    python setup.py build_ext --include-dirs=./include --library-dirs=./lib/x64

5. Install aiortc::

    python setup.py install
6. Go to the :code:`bin/x64` folder, take the vpx and opus dll files, and copy them to :code:`C:\Users\Username\Anaconda3\Library\bin`


Finally, run::

    pip install rtcbot
