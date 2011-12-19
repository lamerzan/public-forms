#!/usr/bin/env python

# Bootstrap installation of Distribute
from importlib import import_module

import os, sys

from distutils.core import setup
from distutils.command.install import install
from setuptools.command.develop import develop
import subprocess

# from subprocess import call
# command = partial(subprocess.call, shell=True, stdout=sys.stdout, stdin=sys.stdin)

def package_env(file_name, strict=False):
    file_path = os.path.join(os.path.dirname(__file__),file_name)
    if os.path.exists(file_path) or strict:
        return open(file_path).read()
    else:
        return u''

PACKAGE = u'public-forms'
PROJECT = u'public_forms'
PROJECT_SLUG = u'public_forms'

VERSION = package_env('VERSION')
URL = package_env('URL')
AUTHOR_AND_EMAIL = [v.strip('>').strip() for v \
                        in package_env('AUTHOR').split('<mailto:')]
if len(AUTHOR_AND_EMAIL)==2:
    AUTHOR, AUTHOR_EMAIL = AUTHOR_AND_EMAIL
else:
    AUTHOR = AUTHOR_AND_EMAIL
    AUTHOR_EMAIL = u''

DESC = "feincms extension templated from django.contrib.skeleton.application"

PACKAGE_NAMESPACE = [s for s in 'feincms.page.extensions'.strip()\
                                                     .strip('"')\
                                                     .strip("'")\
                                                     .strip()\
                                                     .split('.') if s]

NSLIST = lambda sep:(sep.join(PACKAGE_NAMESPACE[:i+1]) for i,n in enumerate(PACKAGE_NAMESPACE))

PACKAGE_NAMESPACE_WITH_PACKAGE = PACKAGE_NAMESPACE + [PROJECT_SLUG,]
NSLIST_WITH_PACKAGE = lambda sep:(sep.join(PACKAGE_NAMESPACE_WITH_PACKAGE[:i+1]) \
                                  for i,n in enumerate(PACKAGE_NAMESPACE_WITH_PACKAGE))

PACKAGE_DIRS = dict(zip(NSLIST_WITH_PACKAGE('.'), 
                       NSLIST_WITH_PACKAGE('/')))

class install_requirements(object):
    def install_requirements(self):
        if os.environ.get('INSTALL_SKELETON_REQUIREMENTS', False):
            for r in self.requirements:
                if os.path.exists(r):
                    subprocess.call('pip install -r %s'%r,
                                    shell=True,
                                    stdout=sys.stdout,
                                    stderr=sys.stderr)

class post_install(install, install_requirements):
    requirements = ['requirements.txt']
    def run(self):
        install.run(self)
        self.install_requirements()

class post_develop(develop, install_requirements):
    requirements = ['requirements.txt', 'requirements.dev.txt']
    def run(self):
        develop.run(self)
        self.install_requirements()
    

if __name__ == '__main__':
    setup(
        cmdclass={"install": post_install,
                   "develop": post_develop,},
        name=PROJECT,
        version=VERSION,
        description=DESC,
        long_description=package_env('README.rst'),
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        url=URL,
        license=package_env('LICENSE'),
        namespace_packages=list(NSLIST('.')),
        packages=list(NSLIST_WITH_PACKAGE('.')),
        package_dir=PACKAGE_DIRS,
        include_package_data=True,
        zip_safe=False,
        test_suite = 'tests',
        # install_requires=['argparse.extra',],
        classifiers=[
            'License :: OSI Approved',
            'License :: OSI Approved :: GNU General Public License (GPL)',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2.7',
            'Framework :: Django',
        ],
    )