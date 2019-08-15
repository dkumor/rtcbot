===================
Inputs
===================

The Inputs API is built as a thin wrapper over the identically-named library (`inputs <https://inputs.readthedocs.io/en/latest/index.html>`_).
If you are having issues, check whether they are coming from RTCBot or from the underlying library.

There are three input devices exposed. A :class:`Keyboard`, a :class:`Mouse` and a :class:`Gamepad`.

.. note::
    To get access to Keyboard and Mouse, you might need to either 
    run as adminsitrator, or on Linux, add your user to the :code:`input` group.

.. warning::
    Keyboard support is experimental - it only works in certain environments. 
    You can try it, but don't be surprised if no events show up.


Mouse
++++++++++++++++

To get mouse events, you can run the following::

    import asyncio
    from rtcbot import Mouse

    m = Mouse()

    @m.subscribe
    def onkey(key):
        print(key)

    try:
        asyncio.get_event_loop().run_forever()
    finally:
        m.close()

This code gives the following results:

.. code-block:: text

    {'timestamp': 1552629001.833567, 'code': 'REL_X', 'state': 1, 'event': 'Relative'}
    {'timestamp': 1552629001.833567, 'code': 'REL_Y', 'state': 1, 'event': 'Relative'}
    {'timestamp': 1552629001.841518, 'code': 'REL_X', 'state': 2, 'event': 'Relative'}
    {'timestamp': 1552629001.889522, 'code': 'REL_X', 'state': 2, 'event': 'Relative'}
    {'timestamp': 1552629001.905525, 'code': 'REL_X', 'state': 3, 'event': 'Relative'}
    {'timestamp': 1552629001.905525, 'code': 'REL_Y', 'state': -2, 'event': 'Relative'}
    {'timestamp': 1552629002.16957, 'code': 'REL_X', 'state': 2, 'event': 'Relative'}
    {'timestamp': 1552629004.233588, 'code': 'MSC_SCAN', 'state': 589825, 'event': 'Misc'}
    {'timestamp': 1552629004.233588, 'code': 'BTN_LEFT', 'state': 1, 'event': 'Key'}
    {'timestamp': 1552629004.361593, 'code': 'MSC_SCAN', 'state': 589825, 'event': 'Misc'}
    {'timestamp': 1552629004.361593, 'code': 'BTN_LEFT', 'state': 0, 'event': 'Key'}
    {'timestamp': 1552629005.361596, 'code': 'MSC_SCAN', 'state': 589826, 'event': 'Misc'}
    {'timestamp': 1552629005.361596, 'code': 'BTN_RIGHT', 'state': 1, 'event': 'Key'}

The REL_X and REL_Y codes refer to relative mouse motion. Here, the mouse started by moving 1 unit to the right (REL_X).



Gamepad
++++++++++++++

The Gamepad usually refers to a wired Xbox controller. Connect it to your computer through USB. 
To use the gamepad, you probably don't need administrator access::

    import asyncio
    from rtcbot import Gamepad

    g = Gamepad()

    @g.subscribe
    def onkey(key):
        print(key)

    try:
        asyncio.get_event_loop().run_forever()
    finally:
        g.close()

This code gives the following results:

.. code-block:: text

    {'timestamp': 1552629513.7494, 'code': 'BTN_SOUTH', 'state': 1, 'event': 'Key'}
    {'timestamp': 1552629513.7494, 'code': 'ABS_Y', 'state': -1, 'event': 'Absolute'}
    {'timestamp': 1552629513.969403, 'code': 'BTN_SOUTH', 'state': 0, 'event': 'Key'}
    {'timestamp': 1552629517.089424, 'code': 'ABS_X', 'state': -253, 'event': 'Absolute'}
    {'timestamp': 1552629517.097385, 'code': 'ABS_X', 'state': -64, 'event': 'Absolute'}
    {'timestamp': 1552629517.109388, 'code': 'ABS_X', 'state': -211, 'event': 'Absolute'}
    {'timestamp': 1552629517.117379, 'code': 'ABS_X', 'state': -242, 'event': 'Absolute'}

The resulting events are all button presses and joystick control. For example, ABS_X here refers to the 
horizontal position of the right joystick on a wired Xbox controller.


API
++++++++++++++++

.. automodule:: rtcbot.inputs
    :members:
    :undoc-members:
    :inherited-members:
    :show-inheritance: