Installing RTCBot
=====================

RTCBot uses some very powerful libraries, which can make it a bit difficult to install on some systems.


Raspbian
++++++++++++++

RTCBot requires several dependencies which are best installed using apt-get::

    sudo apt-get install python3-numpy python3-cffi python3-aiohttp \
        libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
        libswscale-dev libswresample-dev libavfilter-dev libopus-dev \
        libvpx-dev pkg-config libsrtp2-dev python3-opencv pulseaudio

Then, you can install rtcbot with pip::

    sudo pip3 install picamera rtcbot

.. warning::
    These instructions were made with reference to Raspbian Buster on the Raspberry Pi 4.
    Some things might work differently on older versions of raspbian.

Ubuntu
+++++++++++

RTCbot requires several dependencies which are best installed using apt-get::

    sudo apt-get install python3-numpy python3-cffi python3-aiohttp \
        libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
        libswscale-dev libswresample-dev libavfilter-dev libopus-dev \
        libvpx-dev pkg-config libsrtp2-dev python3-opencv pulseaudio

Then, you can install rtcbot with pip::

    sudo pip3 install picamera rtcbot

Windows
+++++++++++

To install on Windows, you will want to use Anaconda `Anaconda <https://www.anaconda.com/distribution/#download-section>`_.

.. note::
    These instructions are incomplete. If you succeed in installing rtcbot 
    on windows, please open a pull request with instructions!

Mac
+++++++++++

To install on Mac, you will want to use Anaconda `Anaconda <https://www.anaconda.com/distribution/#download-section>`_.


.. note::
    These instructions are incomplete. If you succeed in installing rtcbot 
    on mac, please open a pull request with instructions!
