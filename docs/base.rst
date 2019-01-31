===================
Base
===================

RTCBot is heavily based upon the concept of data producers, and data consumers.
To that end, all classes that produce data, such as cameras, microphones, and incoming
data streams are considered producers, and all classes that consume data, such as speakers,
video displays or outgoing data streams are considered consumers.

This section of the documentation is built to describe the backend base classes upon which
all of the data streams are based, and to help you create your own producers and consumers
with an API compatible with the rest of RTCBot.

There are 3 main base classes types

    1) :class:`BaseSubscriptionProducer` and :class:`BaseSubscriptionConsumer`
    2) :class:`ThreadedSubscriptionProducer` and :class:`ThreadedSubscriptionConsumer`
    3) :class:`MultiprocessSubscriptionProducer`

The three types allow setting up your own data acquisition and processing code loops without needing to worry about
the asyncio loop (Threaded) or even the GIL (Multiprocess), but also come with the downside of increasing complexity
and communication overhead.

API
++++++++++++++++
.. note:: Unlike elsewhere in RTCBot's documentation, inherited members are not shown here, so some functions available from a class might be hidden if they were defined in a parent.

.. automodule:: rtcbot.base.events
    :members:
    :show-inheritance:
    :private-members:

.. automodule:: rtcbot.base.base
    :members:
    :show-inheritance:
    :private-members:


.. automodule:: rtcbot.base.thread
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: rtcbot.base.multiprocess
    :members:
    :undoc-members:
    :show-inheritance: