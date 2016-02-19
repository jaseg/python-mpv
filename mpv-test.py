#!/usr/bin/env python3

import unittest
from unittest import mock
import math
import threading
from contextlib import contextmanager
import gc
import time

import mpv


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
            self.assertIn(ptype, (int, float, str, mpv.ynbool))

    def test_read(self):
        for name, (ptype, access) in mpv.ALL_PROPERTIES.items():
            if 'r' in access:
                name =  name.replace('-', '_')
                try:
                    with self.swallow_mpv_errors():
                        rv = getattr(self.m, name)
                except Exception as e:
                    raise RuntimeError('Error while testing property', name)
                if rv is not None: # Technically, any property can return None (even if of type e.g. int)
                    self.assertEqual(type(rv), ptype, msg=name)

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
        handler.has_calls([mock.call('loop', 'no'), mock.call('loop', 'inf')])


class TestLifecycle(unittest.TestCase):
    def test_create_destroy(self):
        thread_names = lambda: [ t.name for t in threading.enumerate() ]
        self.assertNotIn('MPVEventHandlerThread', thread_names())
        m = mpv.MPV()
        self.assertIn('MPVEventHandlerThread', thread_names())
        del m
        gc.collect()
        self.assertNotIn('MPVEventHandlerThread', thread_names())


if __name__ == '__main__':
    unittest.main()
