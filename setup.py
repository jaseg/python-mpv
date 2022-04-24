#!/usr/bin/env python3

from setuptools import setup
from pathlib import Path

setup(
    name = 'python-mpv',
    version = 'v1.0.1',
    py_modules = ['mpv'],
    description = 'A python interface to the mpv media player',
    long_description = (Path(__file__).parent / 'README.rst').read_text(),
    long_description_content_type = 'text/x-rst',
    url = 'https://github.com/jaseg/python-mpv',
    author = 'jaseg',
    author_email = 'github@jaseg.net',
    license = 'GPLv3+',
    extras_require = {
        'screenshot_raw': ['Pillow']
        },
    tests_require = ['xvfbwrapper'],
    test_suite = 'tests',
    keywords = ['mpv', 'library', 'video', 'audio', 'player', 'display',
        'multimedia'],
    python_requires='>=3.7',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: C',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Multimedia :: Sound/Audio :: Players',
        'Topic :: Multimedia :: Video :: Display']
)
