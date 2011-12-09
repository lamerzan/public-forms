from utility import VirtualProjectTestCase


class TestImportable(VirtualProjectTestCase):
    def test_package_importable(self):
        out, err = self.command('''python -c "from feincms.page.extensions import gridsystem; print gridsystem; print gridsystem; print 333333;"''', output=True)
        out = '%s'%out
        self.assert_('feincms.page.extensions' in out)
        self.assert_('gridsystem' in out)
        self.assert_('module' in out)
        self.assert_('333333' in out)
