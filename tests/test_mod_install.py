"""Local configuration preservation, independent of original gameplay."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('install_crash_mod', ROOT/'tools/install_crash_mod.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

class TestModInstall(unittest.TestCase):
    def test_additive_settings_and_idempotence(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=pathlib.Path(scratch)
            before={'ModsConfigured':True,'ActiveMods':['other'],'Unrelated':{'keep':1}}
            settings=root/'settings.json'; settings.write_text(json.dumps(before))
            installer.install(root)
            after=json.loads(settings.read_text())
            self.assertEqual(after['ActiveMods'],['other','cm64-coin-jump'])
            self.assertEqual(after['Unrelated'],before['Unrelated'])
            backups=list(root.glob('settings.before-cm64-*.json'))
            self.assertEqual(len(backups),1)
            self.assertEqual(json.loads(backups[0].read_text()),before)
            installer.install(root)
            self.assertEqual(len(list(root.glob('settings.before-cm64-*.json'))),1)

    def test_disabled_saved_mods_stay_disabled(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=pathlib.Path(scratch)
            (root/'settings.json').write_text(json.dumps({'ModsConfigured':False,'ActiveMods':['old-disabled']}))
            installer.install(root)
            self.assertEqual(json.loads((root/'settings.json').read_text())['ActiveMods'],['cm64-coin-jump'])

    def test_preserves_user_mod_edits(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=pathlib.Path(scratch); installer.install(root)
            source=root/'mods/cm64-coin-jump/CoinJumpMod.cs'
            source.write_text('// user local edit\n')
            with self.assertRaisesRegex(ValueError,'Preserve edited mod'):
                installer.install(root)
            self.assertEqual(source.read_text(),'// user local edit\n')

if __name__=='__main__': unittest.main()
