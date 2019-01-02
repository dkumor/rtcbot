import sounddevice as sd

for i in sd.query_devices():
    if i["max_input_channels"] > 0:
        print(i)
    pass


class AudioSubscription:
    """
    An AudioSubscription gives asynchronous access to the raw audio data.
    It is returned 
    """

    def __init__(self):
        pass


class Audio:
    """
    Reads microphone data, and writes audio output. This class allows you to
    output sound while reading it.
    """
