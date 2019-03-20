Installing RTCBot
=====================

RTCBot uses some very powerful libraries, which can make it a bit difficult to install on some systems.


Raspberry Pi
++++++++++++++

The raspberry pi does not have OpenCV available for python3, 
meaning that RTCBot's CVCamera and CVDisplay will not be available unless you manually compile them.
Thankfully, you can still use the official camera module, by installing picamera::

    sudo apt-get install python3-numpy

Then, you can install rtcbot with pip::

    sudo pip3 install picamera rtcbot

The installation will take a long time, since many of RTCBot's dependencies need to be compiled.

Linux
+++++++++++

Before starting, you will want to install OpenCV, numpy and ffmpeg::

    sudo apt-get install python3-numpy python3-opencv ffmpeg

Then, you can install rtcbot using pip::

    pip3 install rtcbot

Windows
+++++++++++

To install on Windows, you will need to use Anaconda. With anaconda, install opencv, numpy, ...

Then ...

Mac
+++++++++++

On mac, follow the windows instructions - the library will only work through anaconda.