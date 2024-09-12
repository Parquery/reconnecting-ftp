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

setup(name='reconnecting_ftp',
      version='1.1.2',
      description='Reconnecting FTP client',
      long_description=long_description,
      url='https://github.com/Parquery/reconnecting-ftp',
      author='Marko Ristin',
      author_email='marko@ristin.ch',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
      ],
      keywords='ftplib reconnect retry robust ftp client',
      packages=find_packages(exclude=['tests*']),
      install_requires=[],
      extras_require={
          'test': ['pyftpdlib'],
          'dev': ['mypy==1.4.1', 'pylint==2.17.7', 'yapf==0.40.2', 'pyftpdlib', 'coverage==7.2.7']
      },
      py_modules=['reconnecting_ftp'])
