#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
#
# Python MPV library module
# Copyright (C) 2017-2022 Sebastian Götte <code@jaseg.net>
#
# This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import unittest
from unittest import mock
import threading
from contextlib import contextmanager
import os.path
import os
import time
from concurrent.futures import Future

os.environ["PATH"] = os.path.dirname(__file__) + os.pathsep + os.environ["PATH"]

import mpv


if os.name == 'nt':
  Display = mock.Mock()
  testvo='gpu'

else:
  from pyvirtualdisplay import Display
  testvo='x11'


TESTVID = os.path.join(os.path.dirname(__file__), 'test.webm')
TESTSRT = os.path.join(os.path.dirname(__file__), 'sub_test.srt')
MPV_ERRORS = [ l(ec) for ec, l in mpv.ErrorCode.EXCEPTION_DICT.items() if l ]
SKIP_TESTS = os.environ.get('PY_MPV_SKIP_TESTS', '').split()


def timed_print():
    start_time = time.time()
    def do_print(level, prefix, text):
        td = time.time() - start_time
        print('{:.3f} [{}] {}: {}'.format(td, level, prefix, text), flush=True)


class MpvTestCase(unittest.TestCase):
    def setUp(self):
        self.disp = Display()
        self.disp.start()
        self.m = mpv.MPV(vo=testvo, loglevel='debug', log_handler=timed_print())

    def tearDown(self):
        self.m.terminate()
        self.disp.stop()


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

    def test_write(self):
        self.m.loop = 'inf'
        self.m.play(TESTVID)
        while self.m.core_idle:
            time.sleep(0.05)
        check_canaries = lambda: os.path.exists('100') or os.path.exists('foo')
        for name in sorted(self.m.property_list):
            # See issue #108 and upstream mpv issues #7919 and #7920.
            if name in ('demuxer', 'audio-demuxer', 'audio-files'):
                continue
            # These may cause files to be created
            if name in ('external-file', 'heartbeat-cmd', 'wid', 'dump-stats', 'log-file') or name.startswith('input-'):
                continue
            # Caues segmentation faults on wayland
            if name in ('current-window-scale',):
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

    def test_property_observer_decorator(self):
        handler = mock.Mock()

        m = self.m
        m.play(TESTVID)

        m.slang = 'ru'
        m.mute = True

        @m.property_observer('mute')
        @m.property_observer('slang')
        def foo(*args, **kwargs):
            handler(*args, **kwargs)

        m.mute = False
        m.slang = 'jp'
        self.assertEqual(m.mute, False)
        self.assertEqual(m.slang, ['jp'])

        # Wait for tick. AFAICT property events are only generated at regular
        # intervals, and if we change a property too fast we don't get any
        # events. This is a limitation of the upstream API.
        time.sleep(0.1)
        # Another API limitation is that the order of property change events on
        # different properties does not necessarily exactly match the order in
        # which these properties were previously accessed. Thus, any_order.
        handler.assert_has_calls([
            mock.call('mute', False),
            mock.call('slang', ['jp'])],
            any_order=True)
        handler.reset_mock()

        m.mute = True
        m.slang = 'ru'
        self.assertEqual(m.mute, True)
        self.assertEqual(m.slang, ['ru'])

        time.sleep(0.1)
        foo.unobserve_mpv_properties()

        m.mute = False
        m.slang = 'jp'
        m.mute = True
        m.slang = 'ru'
        m.terminate() # needed for synchronization of event thread
        handler.assert_has_calls([
            mock.call('mute', True),
            mock.call('slang', ['ru'])],
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

    def test_wait_for_event_error_forwarding(self):
        self.m.play(TESTVID)

        def check(evt):
            raise ValueError('fnord')

        with self.assertRaises(ValueError):
            self.m.wait_for_event('end_file', cond=check)

    def test_wait_for_property_error_forwarding(self):
        def run():
            nonlocal self
            self.m.wait_until_playing(timeout=2)
            self.m.mute = True
        t = threading.Thread(target=run, daemon=True)
        t.start()

        def cond(mute):
            if mute:
                raise ValueError('fnord')

        with self.assertRaises(ValueError):
            self.m.play(TESTVID)
            self.m.wait_for_property('mute', cond=cond)

    def test_register_simple_decorator_fun_chaining(self):
        self.m.loop = 'inf'
        self.m.play(TESTVID)
        self.m.wait_until_playing(timeout=2)

        handler1, handler2 = mock.Mock(), mock.Mock()

        @self.m.on_key_press('a')
        @self.m.on_key_press('b')
        def reg_test_fun(*args, **kwargs):
            handler1(*args, **kwargs)

        @self.m.on_key_press('c')
        def reg_test_fun_2_stay_intact(*args, **kwargs):
            handler2(*args, **kwargs)

        self.assertEqual(reg_test_fun.mpv_key_bindings, ['b', 'a'])

        def keypress_and_sync(key):
            with self.m.prepare_and_wait_for_event('client_message', timeout=2):
                self.m.keypress(key)

        keypress_and_sync('a')
        handler1.assert_has_calls([ mock.call() ])
        handler2.assert_has_calls([])
        handler1.reset_mock()

        self.m.keypress('x')
        self.m.keypress('X')
        keypress_and_sync('b')
        handler1.assert_has_calls([ mock.call() ])
        handler2.assert_has_calls([])
        handler1.reset_mock()

        keypress_and_sync('c')
        self.m.keypress('B')
        handler1.assert_has_calls([])
        handler2.assert_has_calls([ mock.call() ])
        handler2.reset_mock()

        reg_test_fun.unregister_mpv_key_bindings()
        self.m.keypress('a')
        keypress_and_sync('c')
        self.m.keypress('x')
        self.m.keypress('A')
        handler1.assert_has_calls([])
        handler2.assert_has_calls([ mock.call() ])


class TestStreams(unittest.TestCase):
    def test_python_stream(self):
        handler = mock.Mock()

        disp = Display()
        disp.start()
        m = mpv.MPV(vo=testvo)
        def cb(evt):
            handler(evt.as_dict(decoder=mpv.lazy_decoder))
        m.register_event_callback(cb)

        @m.python_stream('foo')
        def foo_gen():
            with open(TESTVID, 'rb') as f:
                yield f.read()

        @m.python_stream('bar')
        def bar_gen():
            yield b''

        m.play('python://foo')
        m.wait_for_playback()
        handler.assert_any_call({'event': 'end-file', 'reason': 'eof', 'playlist_entry_id': 1})
        handler.reset_mock()

        m.play('python://bar')
        m.wait_for_playback()
        handler.assert_any_call({'event': 'end-file', 'reason': 'error', 'playlist_entry_id': 2, 'file_error': 'unrecognized file format'})
        handler.reset_mock()

        m.play('python://baz')
        m.wait_for_playback()
        handler.assert_any_call({'event': 'end-file', 'reason': 'error', 'playlist_entry_id': 3, 'file_error': 'loading failed'})
        handler.reset_mock()

        m.play('foo://foo')
        m.wait_for_playback()
        handler.assert_any_call({'event': 'end-file', 'reason': 'error', 'playlist_entry_id': 4, 'file_error': 'loading failed'})
        handler.reset_mock()

        foo_gen.unregister()

        m.play('python://foo')
        m.wait_for_playback()
        handler.assert_any_call({'event': 'end-file', 'reason': 'error', 'playlist_entry_id': 5, 'file_error': 'loading failed'})
        handler.reset_mock()

        m.play('python://bar')
        m.wait_for_playback()
        handler.assert_any_call({'event': 'end-file', 'reason': 'error', 'playlist_entry_id': 6, 'file_error': 'unrecognized file format'})
        handler.reset_mock()

        m.terminate()
        disp.stop()

    def test_custom_stream(self):
        handler = mock.Mock()
        fail_mock = mock.Mock(side_effect=ValueError)
        stream_mock = mock.Mock()
        stream_mock.seek = mock.Mock(return_value=0)
        stream_mock.read = mock.Mock(return_value=b'')

        disp = Display()
        disp.start()
        m = mpv.MPV(vo=testvo, video=False)
        def cb(evt):
            handler(evt.as_dict(decoder=mpv.lazy_decoder))
        m.register_event_callback(cb)

        m.register_stream_protocol('pythonfail', fail_mock)

        @m.register_stream_protocol('pythonsuccess')
        def open_fn(uri):
            self.assertEqual(uri, 'pythonsuccess://foo')
            return stream_mock

        m.play('pythondoesnotexist://foo')
        m.wait_for_playback()
        handler.assert_any_call({'event': 'end-file', 'reason': 'error', 'playlist_entry_id': 1, 'file_error': 'loading failed'})
        handler.reset_mock()

        m.play('pythonfail://foo')
        m.wait_for_playback()
        handler.assert_any_call({'event': 'end-file', 'reason': 'error', 'playlist_entry_id': 2, 'file_error': 'loading failed'})
        handler.reset_mock()

        m.play('pythonsuccess://foo')
        m.wait_for_playback()
        stream_mock.seek.assert_any_call(0)
        stream_mock.read.assert_called()
        handler.assert_any_call({'event': 'end-file', 'reason': 'error', 'playlist_entry_id': 3, 'file_error': 'unrecognized file format'})

        m.terminate()
        disp.stop()

    def test_stream_open_exception(self):
        disp = Display()
        disp.start()
        m = mpv.MPV(vo=testvo, video=False)

        @m.register_stream_protocol('raiseerror')
        def open_fn(uri):
            raise SystemError()

        waiting = threading.Semaphore()
        result = Future()
        def run():
            result.set_running_or_notify_cancel()
            try:
                waiting.release()
                m.wait_for_playback()
                result.set_result(False)
            except SystemError:
                result.set_result(True)
            except Exception:
                result.set_result(False)

        t = threading.Thread(target=run, daemon=True)
        t.start()

        with waiting:
            time.sleep(0.2)
            m.play('raiseerror://foo')

        m.wait_for_playback(catch_errors=False)
        try:
            assert result.result()
        finally:
            m.terminate()
            disp.stop()

    def test_python_stream_exception(self):
        disp = Display()
        disp.start()
        m = mpv.MPV(vo=testvo)

        @m.python_stream('foo')
        def foo_gen():
            with open(TESTVID, 'rb') as f:
                yield f.read(100)
                raise SystemError()

        waiting = threading.Semaphore()
        result = Future()
        def run():
            result.set_running_or_notify_cancel()
            try:
                waiting.release()
                m.wait_for_playback()
                result.set_result(False)
            except SystemError:
                result.set_result(True)
            except Exception:
                result.set_result(False)

        t = threading.Thread(target=run, daemon=True)
        t.start()

        with waiting:
            time.sleep(0.2)
            m.play('python://foo')

        m.wait_for_playback(catch_errors=False)
        try:
            assert result.result()
        finally:
            m.terminate()
            disp.stop()

    def test_stream_open_forward(self):
        disp = Display()
        disp.start()
        m = mpv.MPV(vo=testvo, video=False)

        @m.register_stream_protocol('raiseerror')
        def open_fn(uri):
            raise ValueError()

        waiting = threading.Semaphore()
        result = Future()
        def run():
            result.set_running_or_notify_cancel()
            try:
                waiting.release()
                m.wait_for_playback()
                result.set_result(True)
            except Exception:
                result.set_result(False)

        t = threading.Thread(target=run, daemon=True)
        t.start()

        with waiting:
            time.sleep(0.2)
            m.play('raiseerror://foo')

        m.wait_for_playback(catch_errors=False)
        try:
            assert result.result()
        finally:
            m.terminate()
            disp.stop()



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
        # For compatibility with mpv master (v0.32.0-585-gfba1c681b8) accept both
        self.assertIn(m.loop, ['inf', True])
        self.assertEqual(m.deinterlace, False)
        m.terminate()

    def test_event_callback(self):
        handler = mock.Mock()
        m = mpv.MPV(video=False)
        def cb(evt):
            handler(evt.as_dict(decoder=mpv.lazy_decoder))
        m.register_event_callback(cb)
        m.play(TESTVID)
        m.wait_for_playback()

        m.unregister_event_callback(cb)
        handler.assert_has_calls([
                mock.call({'event': 'start-file', 'playlist_entry_id': 1}),
                mock.call({'event': 'end-file', 'reason': 'error', 'playlist_entry_id': 1, 'file_error': 'no audio or video data played'})
            ], any_order=True)
        time.sleep(1)
        handler.reset_mock()
        m.terminate()
        handler.assert_not_called()

    def test_wait_for_property_negative(self):
        self.disp = Display()
        self.disp.start()
        m = mpv.MPV(vo=testvo)
        m.play(TESTVID)
        result = Future()
        def run():
            nonlocal self
            result.set_running_or_notify_cancel()
            try:
                m.wait_for_property('mute')
                result.set_result(False)
            except mpv.ShutdownError:
                result.set_result(True)
        t = threading.Thread(target=run, daemon=True)
        t.start()
        time.sleep(1)
        m.terminate()
        time.sleep(1)
        t.join()
        self.disp.stop()
        assert result.result()

    def test_wait_for_property_positive(self):
        self.disp = Display()
        self.disp.start()
        handler = mock.Mock()
        m = mpv.MPV(vo=testvo)
        m.play(TESTVID)
        def run():
            nonlocal self
            m.wait_for_property('mute')
            handler()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        m.wait_until_playing(timeout=2)
        m.mute = True
        t.join()
        m.terminate()
        time.sleep(1)
        handler.assert_called()
        self.disp.stop()

    def test_wait_for_event(self):
        self.disp = Display()
        self.disp.start()
        m = mpv.MPV(vo=testvo)
        m.play(TESTVID)
        result = Future()
        def run():
            nonlocal self
            result.set_running_or_notify_cancel()
            try:
                m.wait_for_event('seek')
                result.set_result(False)
            except mpv.ShutdownError:
                result.set_result(True)
        t = threading.Thread(target=run, daemon=True)
        t.start()
        time.sleep(1)
        m.terminate()
        t.join()
        self.disp.stop()
        assert result.result()

    def test_wait_for_property_shutdown(self):
        self.disp = Display()
        self.disp.start()
        m = mpv.MPV(vo=testvo)
        m.play(TESTVID)
        with self.assertRaises(mpv.ShutdownError):
            # level_sensitive=false needed to prevent get_property on dead
            # handle
            with m.prepare_and_wait_for_property('mute', level_sensitive=False):
                m.terminate()
        time.sleep(1)
        self.disp.stop()

    @unittest.skipIf('test_wait_for_property_event_overflow' in SKIP_TESTS, reason="kills X-Server first")
    def test_wait_for_property_event_overflow(self):
        self.disp = Display()
        self.disp.start()
        m = mpv.MPV(vo=testvo)
        m.play(TESTVID)
        with self.assertRaises(mpv.EventOverflowError):
            # level_sensitive=false needed to prevent get_property on dead
            # handle
            with m.prepare_and_wait_for_property('mute', cond=lambda val: time.sleep(0.001)):
                for i in range(10000):
                    try:
                        # We really have to try hard to fill up the queue here. Simple async commands will not work,
                        # since then command_async will throw a memory error first. Property changes also do not work,
                        # since they are only processsed when the event loop is idle. This here works reliably.
                        m.command_async('script-message', 'foo', 'bar')
                    except:
                        pass
        m.terminate()
        time.sleep(1)
        self.disp.stop()

    def test_wait_for_event_shutdown(self):
        self.disp = Display()
        self.disp.start()
        m = mpv.MPV(vo=testvo)
        m.play(TESTVID)
        with self.assertRaises(mpv.ShutdownError):
            with m.prepare_and_wait_for_event('seek'):
                m.terminate()
        self.disp.stop()

    def test_wait_for_shutdown(self):
        self.disp = Display()
        self.disp.start()
        m = mpv.MPV(vo=testvo)
        m.play(TESTVID)
        with self.assertRaises(mpv.ShutdownError):
            with m.prepare_and_wait_for_event(None) as result:
                m.terminate()
            result.result()
        self.disp.stop()

    def test_log_handler(self):
        handler = mock.Mock()
        self.disp = Display()
        self.disp.start()
        m = mpv.MPV(vo=testvo, log_handler=handler)
        m.play(TESTVID)
        # Wait for playback to start
        m.wait_until_playing(timeout=2)
        m.command("print-text", 'This is a python-mpv test')
        m.wait_for_playback()
        m.terminate()
        for call in handler.mock_calls:
            _1, (a, b, c), _2 = call
            if a == 'info' and b == 'cplayer' and 'This is a python-mpv test' in c:
                break
        else:
            self.fail('"Test log entry not found in log handler calls: '+','.join(repr(call) for call in handler.mock_calls))
        self.disp.stop()


class CommandTests(MpvTestCase):

    def test_loadfile_with_subtitles(self):
        handler = mock.Mock()
        self.m.property_observer('sub-text')(handler)

        self.m.loadfile(TESTVID, sub_file=TESTSRT)

        self.m.wait_for_playback()
        handler.assert_any_call('sub-text', 'This is\na subtitle test.')
        handler.assert_any_call('sub-text', 'This is the second subtitle line.')

    def test_sub_add(self):
        handler = mock.Mock()
        self.m.property_observer('sub-text')(handler)
        time.sleep(0.5)

        self.m.loadfile(TESTVID)
        self.m.wait_until_playing(timeout=2)
        self.m.sub_add(TESTSRT)

        self.m.wait_for_playback()
        handler.assert_any_call('sub-text', 'This is\na subtitle test.')
        handler.assert_any_call('sub-text', 'This is the second subtitle line.')

    def test_async_command(self):
        handler = mock.Mock()
        callback = mock.Mock()
        self.m.property_observer('sub-text')(handler)
        time.sleep(0.5)

        self.m.loadfile(TESTVID)
        self.m.wait_until_playing(timeout=2)
        self.m.command_async('sub_add', TESTSRT, callback=callback)
        reply = self.m.command_async('expand-text', 'test ${mute}')
        assert reply.result() == 'test no'

        self.m.wait_for_playback()
        handler.assert_any_call('sub-text', 'This is\na subtitle test.')
        handler.assert_any_call('sub-text', 'This is the second subtitle line.')
        callback.assert_any_call(None, None)


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

        m.slang = 'ru'
        time.sleep(0.5)

        m.observe_property('slang', t.t)
        time.sleep(0.5)

        m.slang = 'jp'
        time.sleep(0.5)

        m.slang = 'ru'
        time.sleep(0.5)

        m.unobserve_property('slang', t.t)
        time.sleep(0.5)

        m.slang = 'jp'
        m.slang = 'ru'
        m.terminate() # needed for synchronization of event thread
        handler.assert_has_calls([mock.call('slang', ['jp']), mock.call('slang', ['ru'])])
