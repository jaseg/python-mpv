python-mpv
==========

python-mpv is a ctypes-based python interface to the mpv media player. It gives you more or less full control of all
features of the player, just as the lua interface does.

Installation
============
```bash
wget -O mpv.py https://raw.githubusercontent.com/jaseg/python-mpv/master/mpv.py
```

Seriously though, part of the idea of this being all in one handy file is that you can just copy it into your project.
That also means you don't need to be afraid of customizing it, as it's really not a lot of code. 

Usage
=====
```python
import mpv
player = mpv.MPV(ytdl=True)
player.play('https://youtu.be/DOmdB7D-pUU')
```

Threading
---------
The ```mpv``` module starts one thread for event handling, since MPV sends events that must be processed quickly. The event queue has a fixed maxmimum size and some operations can cause a large number of events to be sent.

If you want to handle threading yourself, you can pass ```start_event_thread=False``` to the ```MPV``` constructor and manually call the ```MPV``` object's ```_loop``` function. There is also an out-of-date branch on the repo that you can cherry-pick that brings in asyncio.

All API functions are thread-safe. If one is not, please file an issue on github.

Advanced Usage
==============
```python
#!/usr/bin/env python3
import mpv

def my_log(loglevel, component, message):
	print('[{}] {}: {}'.format(loglevel, component, message))

player = mpv.MPV(log_handler=my_log, ytdl=True, input_default_bindings=True, input_vo_keyboard=True)

# Property access, these can be changed at runtime
player.observe_property('time-pos', lambda pos: print('Now playing at {:.2f}s'.format(pos)))
player.fullscreen = True
player.loop = 'inf'
# Option access, in general these require the core to reinitialize
player['vo'] = 'opengl'

def my_q_binding(state, key):
    if state[0] == 'd':
        print('THERE IS NO ESCAPE')
player.register_key_binding('q', my_q_binding)

player.play('https://youtu.be/DLzxrzFCyOs')
player.wait_for_playback()

del player

```
