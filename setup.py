#!/usr/bin/env python

from pathlib import Path

from setuptools import setup

from version import __version__

setup(
    name='chatgpt-enhancer-bot',
    description='Telegram bot for chatgpt and extra toolkit',
    version=__version__,
    packages=['chatgpt_enhancer_bot'],
    author='Petr Lavrov',
    author_email='petr.b.lavrov@gmail.com',
    long_description=Path('README.md').read_text(),
    install_requires=Path('requirements.txt').read_text().split(),
    url='https://github.com/Augmented-development/ChatGPTEnhancerBot',
    py_modules=["chatgpt_enhancer_bot", "version"],
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],

)
