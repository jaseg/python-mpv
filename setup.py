#!/usr/bin/env python3

from setuptools import setup
setup(
    name = 'python-mpv',
    version = '0.3.2',
    py_modules = ['mpv'],
    description = 'A python interface to the mpv media player',
    url = 'https://github.com/jaseg/python-mpv',
    author = 'jaseg',
    author_email = 'github@jaseg.net',
    license = 'AGPLv3+',
    keywords = ['mpv', 'library', 'video', 'audio', 'player', 'display', 'multimedia'],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: C',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.5',
        'Topic :: Multimedia :: Sound/Audio :: Players',
        'Topic :: Multimedia :: Video :: Display'],
    install_requires=['PIL'])
