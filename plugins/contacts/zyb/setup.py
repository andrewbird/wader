import os

from setuptools import setup

version = open(os.path.join('VERSION')).readline().rstrip()

setup(name='wader-plugins-contacts-zyb',
        description='ModemManager contacts plugin for wader',
        download_url="http://www.wader-project.org",
        author='Pablo Marti Gamboa',
        author_email='pmarti@warp.es',
        license='GPL',
        packages=['wader.plugins', 'wader.test'])
