# coding=utf-8
from setuptools import setup

setup(
    name = 'flux_led',
    packages = ['flux_led'],
    version = '0.22',
    description = 'A Python library to communicate with the flux_led smart bulbs',
    author = 'Daniel Høyer Iversen',
    author_email = 'mail@dahoiv.net',
    url = 'https://github.com/Danielhiversen/flux_led',
    license = 'LGPLv3+',
    include_package_data = True,
    keywords = [
        'flux_led',
        'smart bulbs',
        'light',
        ],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ' +
            'GNU Lesser General Public License v3 or later (LGPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    entry_points={
        'console_scripts': [
            'flux_led = flux_led.__main__:main'
        ]
    },
)
