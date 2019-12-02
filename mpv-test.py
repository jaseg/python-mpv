#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

import unittest
from unittest import mock
import math
import threading
from contextlib import contextmanager
from functools import wraps
import gc
import os.path
import os
import sys
import time
import io
import platform
import ctypes

import mpv


# stdout magic to suppress useless libmpv warning messages in unittest output
# See https://eli.thegreenplace.net/2015/redirecting-all-kinds-of-stdout-in-python/
@contextmanager
def devnull_libmpv():
    """ Redirect libmpv stdout into /dev/null while still allowing python to print to stdout as usual """
    if platform.system() != 'Linux':
        # This is only a linux-specific convenience function.
        yield
        return

    libc = ctypes.CDLL("libc.so.6")

    stderr_fd, stdout_fd = sys.stderr.fileno(), sys.stdout.fileno()
    sys.stderr.flush()
    sys.stdout.flush()
    libc.fflush(None)

    # Preserve a copy so python can continue printing
    stderr_copy, stdout_copy = os.dup(stderr_fd), os.dup(stdout_fd)
    sys.stderr = io.TextIOWrapper(open(stderr_copy, 'wb', closefd=False), write_through=True)
    sys.stdout = io.TextIOWrapper(open(stdout_copy, 'wb', closefd=False))
    with open(os.devnull, 'w') as devnull:
        os.dup2(devnull.fileno(), stderr_fd) # closes old stderr
        os.dup2(devnull.fileno(), stdout_fd) # closes old stdout

    yield

    sys.stderr.flush()
    sys.stdout.flush()
    libc.fflush(None)
    os.dup2(stderr_copy, stderr_fd)
    os.dup2(stdout_copy, stdout_fd)
    os.close(stderr_copy)
    os.close(stdout_copy)
    sys.stderr = io.TextIOWrapper(open(stderr_fd, 'wb', closefd=False), write_through=True)
    sys.stdout = io.TextIOWrapper(open(stdout_fd, 'wb', closefd=False))

TESTVID = os.path.join(os.path.dirname(__file__), 'test.webm')
MPV_ERRORS = [ l(ec) for ec, l in mpv.ErrorCode.EXCEPTION_DICT.items() if l ]

class MpvTestCase(unittest.TestCase):
    def setUp(self):
        self.m = mpv.MPV()

    def tearDown(self):
        self.m.terminate()

class TestProperties(MpvTestCase):
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

    @devnull_libmpv()
    def test_read(self):
        self.m.loop = 'inf'
        self.m.play(TESTVID)
        while self.m.core_idle:
            time.sleep(0.05)
        for name in sorted(self.m.property_list):
            name = name.replace('-', '_')
            with self.subTest(property_name=name), self.swallow_mpv_errors([
                mpv.ErrorCode.PROPERTY_UNAVAILABLE,
                mpv.ErrorCode.PROPERTY_ERROR,
                mpv.ErrorCode.PROPERTY_NOT_FOUND]):
                getattr(self.m, name)

    @devnull_libmpv()
    def test_write(self):
        self.m.loop = 'inf'
        self.m.play(TESTVID)
        while self.m.core_idle:
            time.sleep(0.05)
        check_canaries = lambda: os.path.exists('100') or os.path.exists('foo')
        for name in sorted(self.m.property_list):
            if name in ('external-file', 'heartbeat-cmd', 'wid', 'dump-stats', 'log-file') or name.startswith('input-'):
                continue
            name =  name.replace('-', '_')
            old_canaries = check_canaries()
            with self.subTest(property_name=name), self.swallow_mpv_errors([
                    mpv.ErrorCode.PROPERTY_UNAVAILABLE,
                    mpv.ErrorCode.PROPERTY_ERROR,
                    mpv.ErrorCode.PROPERTY_FORMAT,
                    mpv.ErrorCode.PROPERTY_NOT_FOUND]): # This is due to a bug with option-mapped properties in mpv 0.18.1
                    setattr(self.m, name, 100)
                    setattr(self.m, name, 1)
                    setattr(self.m, name, 0)
                    setattr(self.m, name, -1)
                    setattr(self.m, name, 1)
                    setattr(self.m, name, 1.0)
                    setattr(self.m, name, 0.0)
                    setattr(self.m, name, -1.0)
                    setattr(self.m, name, float('nan'))
                    setattr(self.m, name, 'foo')
                    setattr(self.m, name, '')
                    setattr(self.m, name, 'bazbazbaz'*1000)
                    setattr(self.m, name, b'foo')
                    setattr(self.m, name, b'')
                    setattr(self.m, name, b'bazbazbaz'*1000)
                    setattr(self.m, name, True)
                    setattr(self.m, name, False)
            if not old_canaries and check_canaries():
                raise UserWarning('Property test for {} produced files on file system, might not be safe.'.format(name))

    def test_property_bounce(self):
        self.m.aid = False
        self.assertEqual(self.m.audio, False)
        self.m.aid = 'auto'
        self.assertEqual(self.m.audio, 'auto')
        self.m.aid = 'no'
        self.assertEqual(self.m.audio, False)
        self.m.audio = 'auto'
        self.assertEqual(self.m.aid, 'auto')
        self.m.audio = False
        self.assertEqual(self.m.aid, False)
        self.m.audio = 'auto'
        self.assertEqual(self.m.aid, 'auto')
        self.m.audio = 'no'
        self.assertEqual(self.m.aid, False)

    def test_array_property_bounce(self):
        self.m.alang = 'en'
        self.assertEqual(self.m.alang, ['en'])
        self.m.alang = 'de'
        self.assertEqual(self.m.alang, ['de'])
        self.m.alang = ['de', 'en']
        self.assertEqual(self.m.alang, ['de', 'en'])
        self.m.alang = 'de,en'
        self.assertEqual(self.m.alang, ['de', 'en'])
        self.m.alang = ['de,en']
        self.assertEqual(self.m.alang, ['de,en'])

    def test_osd_property_bounce(self):
        self.m.alang = ['en']
        self.assertEqual(self.m.osd.alang, 'en')
        self.m.alang = ['de']
        self.assertEqual(self.m.osd.alang, 'de')
        self.m.alang = ['en', 'de']
        self.assertEqual(self.m.osd.alang, 'en,de')

    def test_raw_property_bounce(self):
        self.m.alang = 'en'
        self.assertEqual(self.m.raw.alang, [b'en'])
        self.m.alang = 'de'
        self.assertEqual(self.m.raw.alang, [b'de'])
        self.m.alang = ['de', 'en']
        self.assertEqual(self.m.raw.alang, [b'de', b'en'])
        self.m.alang = 'de,en'
        self.assertEqual(self.m.raw.alang, [b'de', b'en'])
        self.m.alang = ['de,en']
        self.assertEqual(self.m.raw.alang, [b'de,en'])

    def test_property_decoding_invalid_utf8(self):
        invalid_utf8 = b'foo\xc3\x28bar'
        self.m.alang = invalid_utf8
        self.assertEqual(self.m.raw.alang, [invalid_utf8])
        with self.assertRaises(UnicodeDecodeError):
            self.m.strict.alang
        with self.assertRaises(UnicodeDecodeError):
            # alang is considered safe and pasted straight into the OSD string. But OSD strings should always be valid
            # UTF-8. This test may be removed in case OSD encoding sanitization is handled differently in the future.
            self.m.osd.alang

    def test_property_decoding_valid_utf8(self):
        valid_utf8 = 'pröpérty'
        self.m.alang = valid_utf8
        self.assertEqual(self.m.alang, [valid_utf8])
        self.assertEqual(self.m.raw.alang, [valid_utf8.encode('utf-8')])
        self.assertEqual(self.m.osd.alang, valid_utf8)
        self.assertEqual(self.m.strict.alang, [valid_utf8])

    def test_property_decoding_multi(self):
        valid_utf8 = 'pröpérty'
        invalid_utf8 = b'foo\xc3\x28bar'
        self.m.alang = [valid_utf8, 'foo', invalid_utf8]
        self.assertEqual(self.m.alang, [valid_utf8, 'foo', invalid_utf8])
        self.assertEqual(self.m.raw.alang, [valid_utf8.encode('utf-8'), b'foo', invalid_utf8])
        with self.assertRaises(UnicodeDecodeError):
            self.m.strict.alang
        with self.assertRaises(UnicodeDecodeError):
            # See comment in test_property_decoding_invalid_utf8
            self.m.osd.alang

    @devnull_libmpv()
    def test_option_read(self):
        self.m.loop = 'inf'
        self.m.play(TESTVID)
        while self.m.core_idle:
            time.sleep(0.05)
        for name in sorted(self.m):
            with self.subTest(option_name=name), self.swallow_mpv_errors([
                mpv.ErrorCode.PROPERTY_UNAVAILABLE, mpv.ErrorCode.PROPERTY_NOT_FOUND, mpv.ErrorCode.PROPERTY_ERROR]):
                self.m[name]

    def test_multivalued_option(self):
        self.m['external-files'] = ['test.webm', b'test.webm']
        self.assertEqual(self.m['external-files'], ['test.webm', 'test.webm'])


class ObservePropertyTest(MpvTestCase):
    @devnull_libmpv()
    def test_observe_property(self):
        handler = mock.Mock()

        m = self.m
        m.observe_property('vid', handler)

        time.sleep(0.1)
        m.play(TESTVID)

        time.sleep(0.5) #couple frames
        m.unobserve_property('vid', handler)

        time.sleep(0.1) #couple frames
        m.terminate() # needed for synchronization of event thread
        handler.assert_has_calls([mock.call('vid', 'auto')])

    @devnull_libmpv()
    def test_property_observer_decorator(self):
        handler = mock.Mock()

        m = self.m
        m.play(TESTVID)

        m.loop = 'inf'
        m.mute = True

        @m.property_observer('mute')
        @m.property_observer('loop')
        def foo(*args, **kwargs):
            handler(*args, **kwargs)

        m.mute = False
        m.loop = False
        self.assertEqual(m.mute, False)
        self.assertEqual(m.loop, False)

        # Wait for tick. AFAICT property events are only generated at regular
        # intervals, and if we change a property too fast we don't get any
        # events. This is a limitation of the upstream API.
        time.sleep(0.1)
        # Another API limitation is that the order of property change events on
        # different properties does not necessarily exactly match the order in
        # which these properties were previously accessed. Thus, any_order.
        handler.assert_has_calls([
            mock.call('mute', False),
            mock.call('loop', False)],
            any_order=True)
        handler.reset_mock()

        m.mute = True
        m.loop = 'inf'
        self.assertEqual(m.mute, True)
        self.assertEqual(m.loop, True)

        time.sleep(0.05)
        foo.unobserve_mpv_properties()

        m.mute = False
        m.loop = False
        m.mute = True
        m.loop = 'inf'
        m.terminate() # needed for synchronization of event thread
        handler.assert_has_calls([
            mock.call('mute', True),
            mock.call('loop', True)],
            any_order=True)

class KeyBindingTest(MpvTestCase):
    def test_register_direct_cmd(self):
        self.m.register_key_binding('a', 'playlist-clear')
        self.assertEqual(self.m._key_binding_handlers, {})
        self.m.register_key_binding('Ctrl+Shift+a', 'playlist-clear')
        self.m.unregister_key_binding('a')
        self.m.unregister_key_binding('Ctrl+Shift+a')

    def test_register_direct_fun(self):
        b = mpv.MPV._binding_name

        def reg_test_fun(state, name, char):
            pass

        self.m.register_key_binding('a', reg_test_fun)
        self.assertIn(b('a'), self.m._key_binding_handlers)
        self.assertEqual(self.m._key_binding_handlers[b('a')], reg_test_fun)

        self.m.unregister_key_binding('a')
        self.assertNotIn(b('a'), self.m._key_binding_handlers)

    def test_register_direct_bound_method(self):
        b = mpv.MPV._binding_name

        class RegTestCls:
            def method(self, state, name, char):
                pass
        instance = RegTestCls()

        self.m.register_key_binding('a', instance.method)
        self.assertIn(b('a'), self.m._key_binding_handlers)
        self.assertEqual(self.m._key_binding_handlers[b('a')], instance.method)

        self.m.unregister_key_binding('a')
        self.assertNotIn(b('a'), self.m._key_binding_handlers)

    def test_register_decorator_fun(self):
        b = mpv.MPV._binding_name

        @self.m.key_binding('a')
        def reg_test_fun(state, name, char):
            pass
        self.assertEqual(reg_test_fun.mpv_key_bindings, ['a'])
        self.assertIn(b('a'), self.m._key_binding_handlers)
        self.assertEqual(self.m._key_binding_handlers[b('a')], reg_test_fun)

        reg_test_fun.unregister_mpv_key_bindings()
        self.assertNotIn(b('a'), self.m._key_binding_handlers)

    def test_register_decorator_fun_chaining(self):
        b = mpv.MPV._binding_name

        @self.m.key_binding('a')
        @self.m.key_binding('b')
        def reg_test_fun(state, name, char):
            pass

        @self.m.key_binding('c')
        def reg_test_fun_2_stay_intact(state, name, char):
            pass

        self.assertEqual(reg_test_fun.mpv_key_bindings, ['b', 'a'])
        self.assertIn(b('a'), self.m._key_binding_handlers)
        self.assertIn(b('b'), self.m._key_binding_handlers)
        self.assertIn(b('c'), self.m._key_binding_handlers)
        self.assertEqual(self.m._key_binding_handlers[b('a')], reg_test_fun)
        self.assertEqual(self.m._key_binding_handlers[b('b')], reg_test_fun)

        reg_test_fun.unregister_mpv_key_bindings()
        self.assertNotIn(b('a'), self.m._key_binding_handlers)
        self.assertNotIn(b('b'), self.m._key_binding_handlers)
        self.assertIn(b('c'), self.m._key_binding_handlers)

    def test_register_simple_decorator_fun_chaining(self):
        b = mpv.MPV._binding_name

        handler1, handler2 = mock.Mock(), mock.Mock()

        @self.m.on_key_press('a')
        @self.m.on_key_press('b')
        def reg_test_fun(*args, **kwargs):
            handler1(*args, **kwargs)

        @self.m.on_key_press('c')
        def reg_test_fun_2_stay_intact(*args, **kwargs):
            handler2(*args, **kwargs)

        self.assertEqual(reg_test_fun.mpv_key_bindings, ['b', 'a'])
        self.assertIn(b('a'), self.m._key_binding_handlers)
        self.assertIn(b('b'), self.m._key_binding_handlers)
        self.assertIn(b('c'), self.m._key_binding_handlers)

        self.m._key_binding_handlers[b('a')]('p-', 'q', None)
        handler1.assert_has_calls([ mock.call() ])
        handler2.assert_has_calls([])
        handler1.reset_mock()
        self.m._key_binding_handlers[b('b')]('p-', 'q', None)
        handler1.assert_has_calls([ mock.call() ])
        handler2.assert_has_calls([])
        self.m._key_binding_handlers[b('c')]('p-', 'q', None)
        handler1.assert_has_calls([])
        handler2.assert_has_calls([ mock.call() ])

        reg_test_fun.unregister_mpv_key_bindings()
        self.assertNotIn(b('a'), self.m._key_binding_handlers)
        self.assertNotIn(b('b'), self.m._key_binding_handlers)
        self.assertIn(b('c'), self.m._key_binding_handlers)

class TestStreams(unittest.TestCase):
    @devnull_libmpv()
    def test_python_stream(self):
        handler = mock.Mock()

        m = mpv.MPV()
        m.register_event_callback(handler)

        @m.python_stream('foo')
        def foo_gen():
            with open(TESTVID, 'rb') as f:
                yield f.read()

        @m.python_stream('bar')
        def bar_gen():
            yield b''

        m.play('python://foo')
        m.wait_for_playback()
        handler.assert_any_call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.EOF, 'error': mpv.ErrorCode.SUCCESS}})
        handler.reset_mock()

        m.play('python://bar')
        m.wait_for_playback()
        handler.assert_any_call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.ERROR, 'error': mpv.ErrorCode.UNKNOWN_FORMAT}})
        handler.reset_mock()

        m.play('python://baz')
        m.wait_for_playback()
        handler.assert_any_call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.ERROR, 'error': mpv.ErrorCode.LOADING_FAILED}})
        handler.reset_mock()

        m.play('foo://foo')
        m.wait_for_playback()
        handler.assert_any_call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.ERROR, 'error': mpv.ErrorCode.LOADING_FAILED}})
        handler.reset_mock()

        foo_gen.unregister()

        m.play('python://foo')
        m.wait_for_playback()
        handler.assert_any_call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.ERROR, 'error': mpv.ErrorCode.LOADING_FAILED}})
        handler.reset_mock()

        m.play('python://bar')
        m.wait_for_playback()
        handler.assert_any_call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.ERROR, 'error': mpv.ErrorCode.UNKNOWN_FORMAT}})
        handler.reset_mock()

        m.terminate()

    def test_custom_stream(self):
        handler = mock.Mock()
        fail_mock = mock.Mock(side_effect=ValueError)
        stream_mock = mock.Mock()
        stream_mock.seek = mock.Mock(return_value=0)
        stream_mock.read = mock.Mock(return_value=b'')

        m = mpv.MPV(video=False)
        m.register_event_callback(handler)

        m.register_stream_protocol('pythonfail', fail_mock)

        @m.register_stream_protocol('pythonsuccess')
        def open_fn(uri):
            self.assertEqual(uri, 'pythonsuccess://foo')
            return stream_mock

        m.play('pythondoesnotexist://foo')
        m.wait_for_playback()
        handler.assert_any_call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.ERROR, 'error': mpv.ErrorCode.LOADING_FAILED}})
        handler.reset_mock()

        m.play('pythonfail://foo')
        m.wait_for_playback()
        handler.assert_any_call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.ERROR, 'error': mpv.ErrorCode.LOADING_FAILED}})
        handler.reset_mock()

        m.play('pythonsuccess://foo')
        m.wait_for_playback()
        stream_mock.seek.assert_any_call(0)
        stream_mock.read.assert_called()
        handler.assert_any_call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.ERROR, 'error': mpv.ErrorCode.UNKNOWN_FORMAT}})

        m.terminate()

class TestLifecycle(unittest.TestCase):
    def test_create_destroy(self):
        thread_names = lambda: [ t.name for t in threading.enumerate() ]
        self.assertNotIn('MPVEventHandlerThread', thread_names())
        m = mpv.MPV()
        self.assertIn('MPVEventHandlerThread', thread_names())
        m.terminate()
        self.assertNotIn('MPVEventHandlerThread', thread_names())

    def test_flags(self):
        with self.assertRaises(AttributeError):
            mpv.MPV('this-option-does-not-exist')
        m = mpv.MPV('cursor-autohide-fs-only', 'fs', video=False)
        self.assertTrue(m.fullscreen)
        self.assertEqual(m.cursor_autohide, 1000)
        m.terminate()

    def test_options(self):
        with self.assertRaises(AttributeError):
            mpv.MPV(this_option_does_not_exists=23)
        m = mpv.MPV(osd_level=0, loop='inf', deinterlace=False)
        self.assertEqual(m.osd_level, 0)
        self.assertEqual(m.loop, True)
        self.assertEqual(m.deinterlace, False)
        m.terminate()

    def test_event_callback(self):
        handler = mock.Mock()
        m = mpv.MPV(video=False)
        m.register_event_callback(handler)
        m.play(TESTVID)
        m.wait_for_playback()

        m.unregister_event_callback(handler)
        handler.assert_has_calls([
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': 6, 'event': None}),
                mock.call({'reply_userdata': 0, 'error': 0, 'event_id': mpv.MpvEventID.END_FILE, 'event': {'reason': mpv.MpvEventEndFile.ERROR, 'error': mpv.ErrorCode.NOTHING_TO_PLAY}})
            ], any_order=True)
        handler.reset_mock()

        m.terminate()
        handler.assert_not_called()

    def test_log_handler(self):
        handler = mock.Mock()
        m = mpv.MPV(video=False, log_handler=handler)
        m.play(TESTVID)
        m.wait_for_playback()
        m.terminate()
        for call in handler.mock_calls:
            _1, (a, b, c), _2 = call
            if a == 'info' and b == 'cplayer' and c.startswith('Playing: '):
                break
        else:
            self.fail('"Playing: foo..." call not found in log handler calls: '+','.join(repr(call) for call in handler.mock_calls))


class RegressionTests(MpvTestCase):

    def test_unobserve_property_runtime_error(self):
        """
        Ensure a `RuntimeError` is not thrown within
        `unobserve_property`.
        """
        handler = mock.Mock()

        self.m.observe_property('loop', handler)

        try:
            self.m.unobserve_property('loop', handler)
        except RuntimeError:
            self.fail(
                """
                "RuntimeError" exception thrown within
                `unobserve_property`
                """,
            )

    def test_instance_method_property_observer(self):
        """
        Ensure that bound method objects can be used as property observers.
        See issue #26
        """
        handler = mock.Mock()
        m = self.m

        class T(object):
            def t(self, *args, **kw):
                handler(*args, **kw)
        t =  T()

        m.loop = 'inf'

        m.observe_property('loop', t.t)

        m.loop = False
        self.assertEqual(m.loop, False)
        # Wait for tick. AFAICT property events are only generated at regular
        # intervals, and if we change a property too fast we don't get any
        # events. This is a limitation of the upstream API.
        time.sleep(0.01)
        m.loop = 'inf'
        self.assertEqual(m.loop, True)

        time.sleep(0.02)
        m.unobserve_property('loop', t.t)

        m.loop = False
        m.loop = 'inf'
        m.terminate() # needed for synchronization of event thread
        handler.assert_has_calls([mock.call('loop', False), mock.call('loop', True)])


if __name__ == '__main__':
    unittest.main()
