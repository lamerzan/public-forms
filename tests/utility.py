
import os
import sys
import contextlib
import subprocess
import unittest
import tempfile

from copy import copy
from uuid import uuid4
from shutil import rmtree
from random import choice

VENV_WRAPPER = """/bin/bash -c 'source %s; %s'"""

@contextlib.contextmanager
def chdir(dirname=None):
    curdir = os.getcwd()
    try:  
        if dirname is not None:
            os.chdir(dirname)
            yield
    finally:
        os.chdir(curdir)



APPLICATION_PACKAGE_PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class VirtualenvTestCase(unittest.TestCase):
    # @classmethod
    # def setUpClass(cls):
    #     cls.initial_test_result = 
    #     unittest.TestResult = SilentTestResult

    # @classmethod
    # def tearDownClass(cls):
    #     unittest.TestResult = cls.initial_test_result
    
    @classmethod
    def setUpClass(cls):
        cls.create_testdir()
        cls.original_argv = copy(sys.argv)
    
    @classmethod
    def tearDownClass(cls):
        sys.argv = cls.original_argv
        cls.destroy_testdirs()
    
    @classmethod
    def create_testdir(cls):
        cls.testdir = tempfile.mkdtemp()
    
    @classmethod
    def destroy_testdirs(cls):
        if os.path.exists(cls.testdir):
            rmtree(cls.testdir)
    
    @classmethod
    def command(self, *args, **kwargs):
        output = kwargs.pop('output', False)
        defaults = dict(stdout=output and subprocess.PIPE or sys.stdout,
                        stderr=output and subprocess.PIPE or sys.stderr,
                        shell=True)
        defaults.update(kwargs)
        args = list(args)
        args[0] = VENV_WRAPPER% (os.path.join(self.testdir, 
                                             'bin', 
                                             'activate'), 
                                args[0])
        if output:
            return subprocess.Popen(*args, **defaults).communicate()
        else:
            return subprocess.call(*args, **defaults)

class VirtualProjectTestCase(VirtualenvTestCase):
    '''One project created per TestCase'''
    requirements = ['django',
                    'django-mptt', 
                    'feincms',
                    '-e git+http://github.com/wardi/django-filebrowser-no-grappelli.git#egg=django-filebrowser']
    tested_module = 'NameError'
    project_branch = 'feincms'

    @classmethod
    def create_project(cls):
        cls.project_package_name = ''.join((choice('qwertyuio') for i in xrange(10)))
        
        create_cmd = 'django-skeleton create --branch=%s project %s %s'%\
                        (cls.project_branch, cls.testdir, cls.project_package_name)
        
        subprocess.call(create_cmd, 
                        shell=True, 
                        stdout=sys.stdout, 
                        stderr=sys.stderr)
        with open(os.path.join(cls.testdir, 'requirements.txt'), 'w') as reqs:
            for req in cls.requirements:
                reqs.write('%s\n'%req)

        cls.command('%s install_requirements'%cls.project_package_name)
        with chdir(APPLICATION_PACKAGE_PATH):
            cls.command('python %s develop'\
                        %os.path.join(APPLICATION_PACKAGE_PATH, 
                                      'setup.py'))
    
    @classmethod
    def setUpClass(cls):
        VirtualenvTestCase.setUpClass.__get__(None, cls)()
        cls.create_project()