#!/usr/bin/env python

"""
Installation for probedock base library
"""

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open("README.rst") as f:
    long_descr = f.read()


setup(
    name='probedock',
    version='0.1.0',
    packages=['probedock'],
    url='https://github.com/probedock/probedock-python',
    license='MIT',
    author='Benjamin Schubert',
    author_email='ben.c.schubert@gmail.com',
    description='Library for Probedock usage in python',
    long_description=long_descr,

    install_requires=[
        "requests",
        "PyYAML"
    ],

    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Quality Assurance',
        'Topic :: Software Development :: Testing',
    ],
)
