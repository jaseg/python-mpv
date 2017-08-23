.. vim: tw=120 sw=4 et

python-mpv
==========

python-mpv is a ctypes-based python interface to the mpv media player. It gives you more or less full control of all
features of the player, just as the lua interface does.

Installation
------------

.. code:: bash

    pip install python-mpv


...though you can also realistically just copy `mpv.py`_ into your project as it's all nicely contained in one file.

Requirements
~~~~~~~~~~~~

libmpv (no kidding!)
....................
``libmpv.so`` either locally (in your current working directory) or somewhere in your system library search path. This
module is somewhat lenient as far as ``libmpv`` versions are concerned but since ``libmpv`` is changing quite frequently
you'll only get all the newest features when using an up-to-date version of this module. The unit tests for this module
do some basic automatic version compatibility checks. If you discover anything missing here, please open an `issue`_ or
submit a `pull request`_ on github.

Python 2.7, 3.5 or 3.6 (officially)
...................................
The ``master`` branch officially only supports recent python releases (3.5 onwards), but there is the somewhat outdated
but functional `py2compat branch`_ providing Python 2 compatibility.

.. _`py2compat branch`: https://github.com/jaseg/python-mpv/tree/py2compat
.. _`issue`: https://github.com/jaseg/python-mpv/issues
.. _`pull request`: https://github.com/jaseg/python-mpv/pulls

Usage
-----

.. code:: python

    import mpv
    player = mpv.MPV(ytdl=True)
    player.play('https://youtu.be/DOmdB7D-pUU')


Threading
~~~~~~~~~

The ``mpv`` module starts one thread for event handling, since MPV sends events that must be processed quickly. The
event queue has a fixed maxmimum size and some operations can cause a large number of events to be sent.

If you want to handle threading yourself, you can pass ``start_event_thread=False`` to the ``MPV`` constructor and
manually call the ``MPV`` object's ``_loop`` function. If you have some strong need to not use threads and use some
external event loop (such as asyncio) instead you can do that, too with some work. The API of the backend C ``libmpv``
has a function for producing a sort of event file descriptor for a handle. You can use that to produce a file descriptor
that can be passed to an event loop to tell it to wake up the python-mpv event handler on every incoming event.

All API functions are thread-safe. If one is not, please file an issue on github.

Advanced Usage
~~~~~~~~~~~~~~

.. code:: python

    #!/usr/bin/env python3
    import mpv

    def my_log(loglevel, component, message):
        print('[{}] {}: {}'.format(loglevel, component, message))

    player = mpv.MPV(log_handler=my_log, ytdl=True, input_default_bindings=True, input_vo_keyboard=True)

    # Property access, these can be changed at runtime
    @player.property_observer('time-pos')
    def time_observer(_name, value):
        # Here, _value is either None if nothing is playing or a float containing
        # fractional seconds since the beginning of the file.
        print('Now playing at {:.2f}s'.format(value))

    player.fullscreen = True
    player.loop_playlist = 'inf'
    # Option access, in general these require the core to reinitialize
    player['vo'] = 'opengl'

    @player.on_key_press('q')
    def my_q_binding():
        print('THERE IS NO ESCAPE')

    @player.on_key_press('s')
    def my_s_binding():
        pillow_img = player.screenshot_raw()
        pillow_img.save('screenshot.png')

    player.play('https://youtu.be/DLzxrzFCyOs')
    player.wait_for_playback()

    del player

.. code:: python

    #!/usr/bin/env python3
    import mpv

    player = mpv.MPV(ytdl=True, input_default_bindings=True, input_vo_keyboard=True)

    player.playlist_append('https://youtu.be/PHIGke6Yzh8')
    player.playlist_append('https://youtu.be/Ji9qSuQapFY')
    player.playlist_append('https://youtu.be/6f78_Tf4Tdk')

    player.playlist_pos = 0

    while True:
        # To modify the playlist, use player.playlist_{append,clear,move,remove}. player.playlist is read-only
        print(player.playlist)
        player.wait_for_playback()

Coding conventions
------------------

The general aim is `PEP 8`_, with liberal application of the "consistency" section. 120 cells line width. Four spaces.
No tabs. Probably don't bother making pure-formatting PRs except if you think it *really* helps readability or it
*really* irks you if you don't.

.. _`PEP 8`: https://www.python.org/dev/peps/pep-0008/
.. _`mpv.py`: https://raw.githubusercontent.com/jaseg/python-mpv/master/mpv.py
