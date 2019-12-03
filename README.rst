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

libmpv
......
``libmpv.so`` either locally (in your current working directory) or somewhere in your system library search path. This
module is somewhat lenient as far as ``libmpv`` versions are concerned but since ``libmpv`` is changing quite frequently
you'll only get all the newest features when using an up-to-date version of this module. The unit tests for this module
do some basic automatic version compatibility checks. If you discover anything missing here, please open an `issue`_ or
submit a `pull request`_ on github.

On Windows you can place libmpv anywhere in your ``%PATH%`` (e.g. next to ``python.exe``) or next to this module's
``mpv.py``.  Before falling back to looking in the mpv module's directory, python-mpv uses the DLL search order built
into ctypes, which is different to the one Windows uses internally. Consult `this stackoverflow post
<https://stackoverflow.com/a/23805306>`__ for details.

Python >= 3.5 (officially)
..........................
The ``master`` branch officially only supports recent python releases (3.5 onwards), but there is the somewhat outdated
but functional `py2compat branch`_ providing Python 2 compatibility.

.. _`py2compat branch`: https://github.com/jaseg/python-mpv/tree/py2compat
.. _`issue`: https://github.com/jaseg/python-mpv/issues
.. _`pull request`: https://github.com/jaseg/python-mpv/pulls

Supported Platforms
...................

**Linux**, **Windows** and **OSX** all seem to work mostly fine. For some notes on the installation on Windows see
`this comment`__. Shared library handling is quite bad on windows, so expect some pain there. On OSX there seems to be
some bug int the event logic. See `issue 36`_ and `issue 61`_ for details. Creating a pyQT window and having mpv draw
into it seems to be a workaround (about 10loc), but in case you want this fixed please weigh in on the issue tracker
since right now there is not many OSX users.

.. __: https://github.com/jaseg/python-mpv/issues/60#issuecomment-352719773
.. _`issue 61`: https://github.com/jaseg/python-mpv/issues/61
.. _`issue 36`: https://github.com/jaseg/python-mpv/issues/36

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

Logging, Properties, Python Key Bindings, Screenshots and youtube-dl
....................................................................

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
    player['vo'] = 'gpu'

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

Playlist handling
.................

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

Directly feeding mpv data from python
.....................................

.. code:: python

    #!/usr/bin/env python3
    import mpv

    player = mpv.MPV()
    @player.python_stream('foo')
    def reader():
        with open('test.webm', 'rb') as f:
            while True:
                yield f.read(1024*1024)

    player.play('python://foo')
    player.wait_for_playback()

PyQT embedding
..............

.. code:: python
    
    #!/usr/bin/env python3
    import mpv
    import sys

    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *

    class Test(QMainWindow):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.container = QWidget(self)
            self.setCentralWidget(self.container)
            self.container.setAttribute(Qt.WA_DontCreateNativeAncestors)
            self.container.setAttribute(Qt.WA_NativeWindow)
            player = mpv.MPV(wid=str(int(self.container.winId())),
                    vo='x11', # You may not need this
                    log_handler=print,
                    loglevel='debug')
            player.play('test.webm')

    app = QApplication(sys.argv)

    # This is necessary since PyQT stomps over the locale settings needed by libmpv.
    # This needs to happen after importing PyQT before creating the first mpv.MPV instance.
    import locale
    locale.setlocale(locale.LC_NUMERIC, 'C')
    win = Test()
    win.show()
    sys.exit(app.exec_())

PyGtk embedding
..............

.. code:: python
    
    #!/usr/bin/env python3
    import gi

    import mpv

    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk


    class MainClass(Gtk.Window):

        def __init__(self):
            super(MainClass, self).__init__()
            self.set_default_size(600, 400)
            self.connect("destroy", self.on_destroy)

            widget = Gtk.Frame()
            self.add(widget)
            self.show_all()

            # Must be created >after< the widget is shown, else property 'window' will be None
            self.mpv = mpv.MPV(wid=str(widget.get_property("window").get_xid()))
            self.mpv.play("test.webm")

        def on_destroy(self, widget, data=None):
            self.mpv.terminate()
            Gtk.main_quit()


    if __name__ == '__main__':
        application = MainClass()
        Gtk.main()

Using OpenGL from PyQT
......................

Github user cosven_ has managed to `make mpv render into a Qt widget using OpenGL
<https://gist.github.com/cosven/b313de2acce1b7e15afda263779c0afc>`__ through this python API.

Coding Conventions
------------------

The general aim is `PEP 8`_, with liberal application of the "consistency" section. 120 cells line width. Four spaces.
No tabs. Probably don't bother making pure-formatting PRs except if you think it *really* helps readability or it
*really* irks you if you don't.

.. _`PEP 8`: https://www.python.org/dev/peps/pep-0008/
.. _`mpv.py`: https://raw.githubusercontent.com/jaseg/python-mpv/master/mpv.py
.. _cosven: https://github.com/cosven
