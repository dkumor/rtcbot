===================
Camera
===================

The Camera API allows you to subscribe to video frames coming in from a webcam.
To use this API, you will need to either have OpenCV installed
(for use with :class:`CVCamera` and :class:`CVDisplay`), have :mod:`picamera` installed to use :class:`PiCamera`.


To install OpenCV on Ubuntu 18.04, use the following command::

    sudo apt-get install python3-opencv

On raspbian or older ubuntu, you can install it with::

    sudo apt-get install python-opencv

If using windows, it is recommended that you use `Anaconda <https://www.anaconda.com/distribution/#download-section>`_, 
and install OpenCV from there.

If on a Raspberry Pi, you don't need OpenCV at all to use the official Pi Camera. All you need to do is install
the python package::

    sudo pip3 install picamera

CVCamera
++++++++++++++++

The CVCamera uses a webcam connected to your computer, and gathers video frames using OpenCV::

    import asyncio
    from rtcbot import CVCamera, CVDisplay

    camera = CVCamera()
    display = CVDisplay()

    display.putSubscription(camera)

    try:
        asyncio.get_event_loop().run_forever()
    finally:
        camera.close()
        display.close()

The frames are gathered as BGR numpy arrays, so you can perform any OpenCV functions you'd like on them.
For example, the following code shows the video in black and white::

    import asyncio
    from rtcbot import CVCamera, CVDisplay
    import cv2

    camera = CVCamera()
    display = CVDisplay()


    @camera.subscribe
    def onFrame(frame):
        bwframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        display.put_nowait(bwframe)


    try:
        asyncio.get_event_loop().run_forever()
    finally:
        camera.close()
        display.close()

PiCamera
++++++++++++++++

This allows you to use the official raspberry pi camera. You can use it in exactly the same way as the OpenCV camera
above, and it returns exactly the same data for the frame::

    import asyncio
    from rtcbot import PiCamera, CVDisplay

    camera = PiCamera()
    display = CVDisplay()

    display.putSubscription(camera)

    try:
        asyncio.get_event_loop().run_forever()
    finally:
        camera.close()
        display.close()

This means that if not using CVDisplay, you don't even need OpenCV installed to stream from you raspberry pi.

API
++++++++++++++++

.. automodule:: rtcbot.camera
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance:
