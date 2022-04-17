#!/usr/bin/env python3

from setuptools import setup
setup(
    name = 'python-mpv',
    version = '0.5.1',
    py_modules = ['mpv'],
    description = 'A python interface to the mpv media player',
    url = 'https://github.com/jaseg/python-mpv',
    author = 'jaseg',
    author_email = 'github@jaseg.net',
    license = 'AGPLv3+',
    extras_require = {
        'screenshot_raw': ['Pillow']
        },
    tests_require = ['xvfbwrapper'],
    test_suite = 'tests',
    keywords = ['mpv', 'library', 'video', 'audio', 'player', 'display',
        'multimedia'],
    python_requires='>=3.7',
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
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
