#!/usr/bin/env python3

import unittest
from unittest import mock
import math
import threading
from contextlib import contextmanager
import gc
import os.path
import time

import mpv


TESTVID = os.path.join(os.path.dirname(__file__), 'test.webm')
MPV_ERRORS = [ l(ec) for ec, l in mpv.ErrorCode.EXCEPTION_DICT.items() if l ]

class TestProperties(unittest.TestCase):
    @contextmanager
    def swallow_mpv_errors(self):
        try:
            yield
        except Exception as e:
            for ex in MPV_ERRORS:
                if e.args[:2] == ex.args:
                    break
            else:
                raise

    def setUp(self):
        self.m = mpv.MPV()

    def test_sanity(self):
        for name, (ptype, access) in mpv.ALL_PROPERTIES.items():
            self.assertTrue('r' in access or 'w' in access)
            self.assertRegex(name, '^[-0-9a-z]+$')
            self.assertIn(ptype, (int, float, str, mpv.ynbool, mpv.commalist))

    def test_completeness(self):
        ledir = dir(self.m)
        for prop in self.m.property_list:
            if prop in ('stream-path', 'demuxer', 'mixer-active'):
                continue # Property is deemed useless by man mpv(1)
            if prop in ('osd-sym-cc', 'osd-ass-cc', 'working-directory'):
                continue # Property is deemed useless by me
            if prop in ('clock', 'keepaspect',
                    'tv-scan', 'tv-channel', 'tv-norm', 'tv-freq',
                    'ff-vid', 'ff-aid', 'ff-sid',
                    'colormatrix-gamma'):
                continue # Property is undocumented in man mpv(1) and we don't want to risk it
            if prop in ('hwdec-active', 'hwdec-detected'):
                continue # Property is deprecated
            prop = prop.replace('-', '_')
            self.assertTrue(prop in ledir, 'Property {} not found'.format(prop))

    def test_read(self):
        for name, (ptype, access) in mpv.ALL_PROPERTIES.items():
            if 'r' in access:
                name =  name.replace('-', '_')
                with self.subTest(property_name=name):
                    with self.swallow_mpv_errors():
                        rv = getattr(self.m, name)
                if rv is not None: # Technically, any property can return None (even if of type e.g. int)
                    self.assertEqual(type(rv), type(ptype()))

    def test_write(self):
        for name, (ptype, access) in mpv.ALL_PROPERTIES.items():
            if 'w' in access:
                name =  name.replace('-', '_')
                with self.swallow_mpv_errors():
                    if ptype == int:
                        setattr(self.m, name, 0)
                        setattr(self.m, name, 1)
                        setattr(self.m, name, -1)
                    elif ptype == float:
                        setattr(self.m, name, 0.0)
                        setattr(self.m, name, 1)
                        setattr(self.m, name, 1.0)
                        setattr(self.m, name, -1.0)
                        setattr(self.m, name, math.nan)
                    elif ptype == str:
                        setattr(self.m, name, 'foo')
                        setattr(self.m, name, '')
                        setattr(self.m, name, 'bazbazbaz'*1000)
                    elif ptype == mpv.ynbool:
                        if 'r' in access:
                            setattr(self.m, name, 'yes')
                            self.assertTrue(getattr(self.m, name))
                            self.assertEqual(getattr(self.m, name), True)
                            setattr(self.m, name, b'yes')
                            self.assertTrue(getattr(self.m, name))
                            setattr(self.m, name, True)
                            self.assertTrue(getattr(self.m, name))

                            setattr(self.m, name, 'no')
                            self.assertFalse(getattr(self.m, name))
                            self.assertEqual(getattr(self.m, name), False)
                            setattr(self.m, name, b'no')
                            self.assertFalse(getattr(self.m, name))
                            setattr(self.m, name, False)
                            self.assertFalse(getattr(self.m, name))
                        else:
                            setattr(self.m, name, 'yes')
                            setattr(self.m, name, b'yes')
                            setattr(self.m, name, True)

    def tearDown(self):
        del self.m

class ObservePropertyTest(unittest.TestCase):
    def test_observe_property(self):
        handler = mock.Mock()

        m = mpv.MPV()
        m.loop = 'inf'

        m.observe_property('loop', handler)

        m.loop = 'no'
        self.assertEqual(m.loop, 'no')

        m.loop = 'inf'
        self.assertEqual(m.loop, 'inf')

        time.sleep(0.02)
        m.unobserve_property(handler)

        m.loop = 'no'
        m.loop = 'inf'
        m.terminate() # needed for synchronization of event thread
        handler.assert_has_calls([mock.call('loop', 'no'), mock.call('loop', 'inf')])


class TestLifecycle(unittest.TestCase):
    def test_create_destroy(self):
        thread_names = lambda: [ t.name for t in threading.enumerate() ]
        self.assertNotIn('MPVEventHandlerThread', thread_names())
        m = mpv.MPV()
        self.assertIn('MPVEventHandlerThread', thread_names())
        del m
        gc.collect()
        self.assertNotIn('MPVEventHandlerThread', thread_names())

    def test_flags(self):
        with self.assertRaises(AttributeError):
            mpv.MPV('this-option-does-not-exist')
        m = mpv.MPV('no-video', 'cursor-autohide-fs-only', 'fs')
        self.assertTrue(m.fullscreen)
        self.assertEqual(m.cursor_autohide, '1000')

    def test_options(self):
        with self.assertRaises(AttributeError):
            mpv.MPV(this_option_does_not_exists=23)
        m = mpv.MPV(osd_level=0, loop='inf', deinterlace='no')
        self.assertEqual(m.osd_level, 0)
        self.assertEqual(m.loop, 'inf')
        self.assertEqual(m.deinterlace, 'no')

    def test_event_callback(self):
        handler = mock.Mock()
        m = mpv.MPV('no-video')
        m.event_callbacks.append(handler)
        m.play(TESTVID)
        m.wait_for_playback()
        del m
        handler.assert_has_calls([
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': 6, 'event': None}),
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': 9, 'event': None}),
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': 7, 'event': {'reason': 4}}),
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': 11, 'event': None}),
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': 1, 'event': None})
            ], any_order=True)
    
    def test_log_handler(self):
        handler = mock.Mock()
        m = mpv.MPV('no-video', log_handler=handler)
        m.play(TESTVID)
        m.wait_for_playback()
        del m
        handler.assert_has_calls([
            mock.call('info', 'cplayer', 'Playing: test.webm'),
            mock.call('info', 'cplayer', '     Video --vid=1 (*) (vp8)'),
            mock.call('fatal', 'cplayer', 'No video or audio streams selected.'),
            mock.call('info', 'cplayer', '')])


if __name__ == '__main__':
    unittest.main()
