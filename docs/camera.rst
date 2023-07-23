===================
Camera
===================

The Camera API allows you to subscribe to video frames coming in from a webcam.
To use this API, you will need to either have OpenCV installed
(for use with :class:`CVCamera` and :class:`CVDisplay`), have :mod:`picamera` installed to use :class:`PiCamera`.


To install OpenCV on Ubuntu 18.04 or Raspbian Buster, use the following command::

    sudo apt-get install python3-opencv

On Raspbian Stretch or older Ubuntu, you can install it with::

    sudo apt-get install python-opencv

If using Windows or Mac, it is recommended that you use `Anaconda <https://www.anaconda.com/distribution/#download-section>`_, 
and install OpenCV from there.

If on a Raspberry Pi, you don't need OpenCV at all to use the official Pi Camera.

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

.. warning::
    There is currently an issue with threading in OpenCV that makes CVDisplay not work on Mac.

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

PiCamera2
++++++++++++++++

This allows you to use the official raspberry pi camera, with libcamera stack (legacy camera interface disabled).
This is default since Raspberry Pi OS bullseye, PiCamera2 also works with 64-bit OS.
You can use the parameter hflip=1 to flip the camera horizontally, vflip=1 to flip vertically, or both to rotate 180 degrees.
You can use it in exactly the same way as the OpenCV camera above, and it returns exactly the same data for the frame::

    import asyncio
    from rtcbot import PiCamera2, CVDisplay

    camera = PiCamera2()
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
