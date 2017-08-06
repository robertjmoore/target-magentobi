#!/usr/bin/env python

from setuptools import setup

setup(name='target-magentobi',
      version='0.1.1',
      description='Singer.io target for the Magento Business Intelligence API',
      author='Robert J. Moore',
      url='http://www.robertjmoore.com/',
      classifiers=['Programming Language :: Python :: 3 :: Only'],
      py_modules=['target_magentobi'],
      install_requires=[
          'jsonschema',
          'mock==2.0.0',
          'requests==2.13.0',
          'singer-python>=0.2.1',
          'strict-rfc3339',
      ],
      entry_points='''
          [console_scripts]
          target-magentobi=target_magentobi:main
      ''',
      packages=['target_magentobi'],
)
