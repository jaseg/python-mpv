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
    def swallow_mpv_errors(self, exception_exceptions=[]):
        try:
            yield
        except Exception as e:
            if any(e.args[:2] == ex.args for ex in MPV_ERRORS):
                if e.args[1] not in exception_exceptions:
                    raise
            else:
                raise

    def setUp(self):
        self.m = mpv.MPV()

    def test_sanity(self):
        for name, (ptype, access, *_args) in mpv.ALL_PROPERTIES.items():
            self.assertTrue('r' in access or 'w' in access)
            self.assertRegex(name, '^[-0-9a-z]+$')
            # Types and MpvFormat values
            self.assertIn(ptype, [bool, int, float, str, bytes, mpv.commalist] + list(range(10)))

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
        self.m.loop = 'inf'
        self.m.play(TESTVID)
        while self.m.core_idle:
            time.sleep(0.05)
        for name, (ptype, access, *_args) in sorted(mpv.ALL_PROPERTIES.items()):
            if 'r' in access:
                name =  name.replace('-', '_')
                with self.subTest(property_name=name), self.swallow_mpv_errors([
                    mpv.ErrorCode.PROPERTY_UNAVAILABLE, mpv.ErrorCode.PROPERTY_ERROR]):
                    rv = getattr(self.m, name)
                    if rv is not None and callable(ptype):
                        # Technically, any property can return None (even if of type e.g. int)
                        self.assertEqual(type(rv), type(ptype()))

    def test_write(self):
        self.m.loop = 'inf'
        self.m.play(TESTVID)
        while self.m.core_idle:
            time.sleep(0.05)
        for name, (ptype, access, *_args) in sorted(mpv.ALL_PROPERTIES.items()):
            if 'w' in access:
                name =  name.replace('-', '_')
                with self.subTest(property_name=name), self.swallow_mpv_errors([
                        mpv.ErrorCode.PROPERTY_UNAVAILABLE,
                        mpv.ErrorCode.PROPERTY_ERROR,
                        mpv.ErrorCode.PROPERTY_FORMAT]): # This is due to a bug with option-mapped properties in mpv 0.18.1
                    if ptype == int:
                        setattr(self.m, name, 0)
                        setattr(self.m, name, 1)
                        setattr(self.m, name, -1)
                    elif ptype == float:
                        setattr(self.m, name, 0.0)
                        setattr(self.m, name, 1)
                        setattr(self.m, name, 1.0)
                        setattr(self.m, name, -1.0)
                        setattr(self.m, name, float('nan'))
                    elif ptype == str:
                        setattr(self.m, name, 'foo')
                        setattr(self.m, name, '')
                        setattr(self.m, name, 'bazbazbaz'*1000)
                    elif ptype == bytes:
                        setattr(self.m, name, b'foo')
                        setattr(self.m, name, b'')
                        setattr(self.m, name, b'bazbazbaz'*1000)
                    elif ptype == bool:
                        setattr(self.m, name, True)
                        setattr(self.m, name, False)

    def test_option_read(self):
        self.m.loop = 'inf'
        self.m.play(TESTVID)
        while self.m.core_idle:
            time.sleep(0.05)
        for name in sorted(self.m):
            with self.subTest(option_name=name), self.swallow_mpv_errors([
                mpv.ErrorCode.PROPERTY_UNAVAILABLE, mpv.ErrorCode.PROPERTY_NOT_FOUND, mpv.ErrorCode.PROPERTY_ERROR]):
                self.m[name]


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
        m.unobserve_property('loop', handler)

        m.loop = 'no'
        m.loop = 'inf'
        m.terminate() # needed for synchronization of event thread
        handler.assert_has_calls([mock.call('no'), mock.call('inf')])


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
        m.register_event_callback(handler)
        m.play(TESTVID)
        m.wait_for_playback()

        m.unregister_event_callback(handler)
        handler.assert_has_calls([
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': 6, 'event': None}),
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': 9, 'event': None}),
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': 7, 'event': {'reason': 4}}),
            ], any_order=True)
        handler.reset_mock()

        del m
        handler.assert_not_called()

    def test_log_handler(self):
        handler = mock.Mock()
        m = mpv.MPV('no-video', log_handler=handler)
        m.play(TESTVID)
        m.wait_for_playback()
        del m
        handler.assert_has_calls([
            mock.call('info', 'cplayer', 'Playing: test.webm'),
            mock.call('info', 'cplayer', '     Video --vid=1 (*) (vp8)'),
            mock.call('fatal', 'cplayer', 'No video or audio streams selected.')])


if __name__ == '__main__':
    unittest.main()
