'''
    setup.py
    --------
    Simple distutils script, which in general streetsign use is probably
    pointless, but nevertheless is kind of useful for ReadTheDocs to be able
    to install streetsign_server as a module in its virtualenv.
'''

from setuptools import setup

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='streetsign_server',
    packages=['streetsign_server', 'streetsign_server.views',
              'streetsign_server.logic',
              'streetsign_server.post_types',
              'streetsign_server.external_source_types'],
    version="1.1.0",
    description='A simple python/flask/web based digital signage system',
    long_description=long_description,
    author='Daniel Fairhead',
    author_email='danthedeckie@gmail.com',
    url='https://github.com/jamswat/streetsign',
    keywords=['flask', 'signage', 'web'],
    python_requires='>=3.10',
    classifiers=['Development Status :: 4 - Beta',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.10',
                 'Programming Language :: Python :: 3.11',
                 'Programming Language :: Python :: 3.12',
                 'Programming Language :: Python :: 3.13',
                 ],
)