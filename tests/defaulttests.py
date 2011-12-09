from utility import VirtualProjectTestCase


class TestImportable(VirtualProjectTestCase):
    def test_package_importable(self):
        out, err = self.command('''python -c "from {package_namespace} import {egg_name}; print {egg_name}; print 'marKer'"''', output=True)
        out = '%s'%out
        self.assert_('{package_namespace}' in out)
        self.assert_('{egg_name}' in out)
        self.assert_('module' in out)
        self.assert_('marKer' in out)
