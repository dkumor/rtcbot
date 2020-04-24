===================
Audio
===================

Audio support is built upon the `SoundCard <https://soundcard.readthedocs.io/en/latest/>`_ library.
The provided API gives a simple asyncio-based wrapper of the library, which integrates directly
with other components of rtcbot.

The library is made up of two objects: a :class:`Speaker` and :class:`Microphone`. 
The Microphone gathers audio at 48000 samples per second, and gives the data in chunks of 1024 samples.
The data is returned as a numpy array of shape :code:`(samples,channels)`.

The speaker performs the reverse operation: it is given numpy arrays containing audio samples, and it plays them
on the computer's default audio output.

Basic Example
++++++++++++++++

With the following code, you can listen to yourself. Make sure to wear headphones, so you don't get feedback::

    import asyncio
    from rtcbot import Microphone, Speaker

    microphone = Microphone()
    speaker = Speaker()

    speaker.putSubscription(microphone)

    try:
        asyncio.get_event_loop().run_forever()
    finally:
        microphone.close()
        speaker.close()

Naturally, the raw data can be manipulated with numpy. For example, the following code makes the output five times as loud::

    import asyncio
    from rtcbot import Microphone, Speaker

    microphone = Microphone()
    speaker = Speaker()

    @microphone.subscribe
    def onData(data):
        data = data * 5
        if speaker.ready:
            speaker.put_nowait(data)

    try:
        asyncio.get_event_loop().run_forever()
    finally:
        microphone.close()
        speaker.close()

By checking if the speaker is ready, we don't queue up audio while it is initializing (if the microphone starts returning data before the speaker is prepared).
This allows us to hear the audio with low latency. This effect was automatic in the first example, 
because a subscription to microphone was not created until :code:`microphone.get` was called by the speaker.


.. warning::
    This is one of the fundamental differences between video and audio in RTCBot - dropping a video frame is not a big deal, 
    so the cameras automatically always
    return the most recent frame. However, dropping audio results in weird audio glitches. To avoid this, audio is *queued*. This means that
    a subscription that is not actively being read will keep queueing up data indefinitely. 
    Make sure to unsubscribe the moment you stop using an audio subscription, or your code will eventually run out of memory!


API
++++++++++++++++

.. automodule:: rtcbot.audio
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance:
