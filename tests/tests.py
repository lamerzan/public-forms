from utility import VirtualProjectTestCase


class TestOfTest(VirtualProjectTestCase):
    def test_of_test0(self):
        out, err = self.command_output('python -c "from pageextensions import gridsystem; print gridsystem"')
        print out
        print err