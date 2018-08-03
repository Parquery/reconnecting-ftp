"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
import os

from setuptools import setup, find_packages

# pylint: disable=redefined-builtin

here = os.path.abspath(os.path.dirname(__file__))  # pylint: disable=invalid-name

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()  # pylint: disable=invalid-name

setup(
    name='reconnecting_ftp',
    version='1.0.12',
    description='Reconnecting FTP client',
    long_description=long_description,
    url='https://github.com/Parquery/reconnecting-ftp',
    author='Marko Ristin',
    author_email='marko@parquery.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='ftplib reconnect retry robust ftp client',
    packages=find_packages(exclude=['tests*']),
    install_requires=[],
    extras_require={
        'test': ['pyftpdlib'],
        'dev': ['mypy==0.560', 'pylint==1.8.2', 'yapf==0.20.2', 'pyftpdlib']
    },
    py_modules=['reconnecting_ftp'])
