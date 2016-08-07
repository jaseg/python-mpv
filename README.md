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

Advanced Usage
==============
```python
#!/usr/bin/env python3
import mpv

def my_log(loglevel, component, message):
	print('[{}] {}: {}'.format(loglevel, component, message))

player = mpv.MPV(log_handler=my_log, ytdl=True)

player.observe_property('time-pos', lambda _property, pos: print('Now playing at {:.2f}s'.format(pos)))
player.fullscreen = True
player.loop = 'inf'

player.play('https://youtu.be/DLzxrzFCyOs')
player.wait_for_playback()

del player

```
