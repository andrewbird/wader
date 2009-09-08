from setuptools import setup, find_packages
import os

version = open(os.path.join('VERSION')).readline().rstrip()

setup(name='wader-plugins-contacts-sqlite',
        description='SQLite contacts plugin for wader',
        download_url="http://www.wader-project.org",
        author='Pablo Marti Gamboa',
        author_email='pmarti@warp.es',
        license='GPL',
        packages=['wader.plugins'],
        namespace_packages=['wader.plugins','wader'],
        )

