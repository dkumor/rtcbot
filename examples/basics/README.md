# RTCBot Basics

This tutorial will teach you the fundamentals of using RTCBot for your projects.
RTCBot is a Python 3 [asyncio](https://docs.python.org/3/library/asyncio.html) library,
meaning that it is meant to run in an event loop.

## Asyncio Basics

The most basic asyncio program is the following:

```python
import asyncio

# Run the event loop
asyncio.get_event_loop().run_forever()
```

You can exit the program with `CTRL+C`. Right now, the program does nothing, just runs in a loop. Let's fix that:

```python
import asyncio

async def myfunction():
    while True:
        await asyncio.sleep(1)
        print("1 second passed")

asyncio.ensure_future(myfunction())
asyncio.get_event_loop().run_forever()
```

This will print "1 second passed" each second.

Notice that `myfunction` is run in an infinite loop.
The utility of an event loop is that you can run many functions _concurrently_, which behaves as if your program was running with many threads at once:

```python
import asyncio

async def myfunction1():
    while True:
        await asyncio.sleep(1)
        print("1 second passed")

async def myfunction2():
    while True:
        await asyncio.sleep(2)
        print("2 seconds passed")

asyncio.ensure_future(myfunction1())
asyncio.ensure_future(myfunction2())
asyncio.get_event_loop().run_forever()
```

The key here is the `await` keyword, used in an `async` function (called a coroutine). The `await asyncio.sleep(1)` command pauses execution of the function until one second has passed,
allowing the event loop to spend time running the other function.

This means that the event loop is a good way to program where multiple things need to happen in response to events, such as incoming data, or timers, which is precisely the situation in a robot.

RTCBot is a set of tools allowing you to easily use an asyncio event loop to pass information
between parts of your robot.

To learn more about asyncio, it is recommended that you look at a more in-depth tutorial [here](https://www.blog.pythonlibrary.org/2016/07/26/python-3-an-intro-to-asyncio/).

## View a Video Feed

To introduce you to the basic concepts of RTCBot, we will start with the simplest task, viewing a webcam video feed:

```python
import asyncio
from rtcbot import CVCamera, CVDisplay

camera = CVCamera()
display = CVDisplay()

@camera.subscribe
def onFrame(frame):
    print("got video frame")
    display.put_nowait(frame)

try:
    asyncio.get_event_loop().run_forever()
finally:
    camera.close()
    display.close()

```

The camera might take several seconds to initialize, but after it finishes, a window with a live
feed of your webcam will pop up.

The `CVCamera` and `CVDisplay` objects use OpenCV in the background to process frames.
The `camera.subscribe` function allows you to subscribe to video frames incoming from the webcam,
firing the `onFrame` function 30 times a second with [numpy](https://en.wikipedia.org/wiki/NumPy) arrays containing BGR images captured by the camera.
The `put_nowait` function is then used to send the frame to the window where the image is displayed.

These two functions are part of RTCBot's core abilities. Every producer of data (like `CVCamera`) has a `subscribe()` method, and every consumer of data (like `CVDisplay`) has a `put_nowait` method to insert data.

```eval_rst
.. note::
    If you are using the official Raspberry Pi camera, you should replace CVCamera with PiCamera.

.. warning::
    CVDisplay does not work on Mac due to issues with threading in the display toolkit - if using a Mac, you'll have to
    wait for the video streaming tutorial to view the video feed!

```

## Subscriptions

Using a callback function with the `subscribe` method is not the only way to 
get data out of a data-producing object. The `subscribe` method is also able
to create what is called a `subscription`.

To understand subscriptions, let's take a quick detour to python Queues:

```python
import asyncio

# An asyncio Queue has put_nowait and get coroutine
q = asyncio.Queue()

# Sends data each second
async def sender():
    while True:
        await asyncio.sleep(1)
        q.put_nowait("hi!")

# Receives the data
async def receiver():
    while True:
        data = await q.get()
        print("Received:", data)

asyncio.ensure_future(sender())
asyncio.ensure_future(receiver())
asyncio.get_event_loop().run_forever()
```

Here, the `sender` function sends data, and the `receiver` awaits for incoming data, and prints it. Notice how the queue had a `get` coroutine from which data could be awaited.

We can use the `subscribe` method in a similar way to the above code snippet. When run without an argument, `subscribe` actually returns a subscription, which `CVCamera` automatically keeps updated with new video frames as they come in:

```python
import asyncio
from rtcbot import CVCamera, CVDisplay

camera = CVCamera()
display = CVDisplay()

frameSubscription = camera.subscribe()

async def receiver():
    while True:
        frame = await frameSubscription.get()
        display.put_nowait(frame)

asyncio.ensure_future(receiver())

try:
    asyncio.get_event_loop().run_forever()
finally:
    camera.close()
    display.close()
```

This program displays a live video feed, just like the previous version.

The `receiver` function is just running `put_nowait` on each frame received from the subscription. This can be done automatically using the `putSubscription` method, making this a shorthand for the above program:

```python
import asyncio
from rtcbot import CVCamera, CVDisplay

camera = CVCamera()
display = CVDisplay()

frameSubscription = camera.subscribe()
display.putSubscription(frameSubscription)

try:
    asyncio.get_event_loop().run_forever()
finally:
    camera.close()
    display.close()
```

Finally, the `camera` object has a `get` coroutine, meaning that it can be passed into `putSubscription` directly:

```python
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
```

## Generalizing to Audio

The above code examples all created a video stream, and displayed it in a window. RTCBot uses _exactly the same_ API for **everything**. This means that we can trivially add audio to the previous example:

```python
import asyncio
from rtcbot import CVCamera, CVDisplay, Microphone, Speaker

camera = CVCamera()
display = CVDisplay()
microphone = Microphone()
speaker = Speaker()

display.putSubscription(camera)
speaker.putSubscription(microphone)

try:
    asyncio.get_event_loop().run_forever()
finally:
    camera.close()
    display.close()
    microphone.close()
    speaker.close()
```

Here, a video stream should be displayed in a window, and all microphone input should be playing in your headphones (or speakers).

## Summary

This tutorial introduced the basics of RTCBot, with a focus on the fundamentals:

1. Every data producer has the `subscribe` method and `get` coroutine
2. Every data consumer has a `putSubscription` method and a `put_nowait` method
3. `putSubscription` takes any object with a `get` coroutine
4. Subscribe can also be used for direct callbacks, or with custom subscriptions.

## Extra Notes

Each producer can have multiple subscriptions active at the same time. This code shows two different windows with the same video feed:

```python
import asyncio
from rtcbot import CVCamera, CVDisplay

camera = CVCamera()
display = CVDisplay()
display2 = CVDisplay()

display.putSubscription(camera)
subscription2 = camera.subscribe()
display2.putSubscription(subscription2)

try:
    asyncio.get_event_loop().run_forever()
finally:
    camera.close()
    display.close()
    display2.close()
```

The `get` coroutine of camera behaves as a single default subscription, so it can only be used by one display (it returns each frame once). The `subscribe` function allows creating an arbitrary number of independent subscriptions/callbacks.
