"""Static checks for the configuration shipped in this starter. Not game-runtime tests."""
import pathlib
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class TestOrchestrationBootstrap(unittest.TestCase):
    def test_root_config(self):
        config=tomllib.loads((ROOT/'.codex/config.toml').read_text())
        self.assertEqual(config['model'],'gpt-6.1-sol')
        self.assertEqual(config['model_reasoning_effort'],'medium')
        self.assertTrue(config['agents']['enabled'])
        self.assertEqual(config['agents']['max_concurrent_threads_per_session'],2)

    def test_subagent_config(self):
        paths=sorted((ROOT/'.codex/agents').glob('*.toml'))
        self.assertEqual(len(paths),5)
        names=set()
        for p in paths:
            agent=tomllib.loads(p.read_text())
            for req in ('name','description','developer_instructions','model','model_reasoning_effort'):
                self.assertTrue(agent.get(req), (p,req))
            self.assertEqual(agent['sandbox_mode'],'read-only')
            self.assertNotIn(agent['name'],names)
            names.add(agent['name'])
            expected='gpt-6-astra' if p.stem.startswith('astra_') else 'gpt-6.1-sol'
            self.assertEqual(agent['model'],expected)
        self.assertEqual(names,{'crash_recon','mario_recon','astra_architect','astra_debugger','qa_reviewer'})

    def test_status_separates_bootstrap_from_real_gameplay(self):
        status=(ROOT/'docs/STATUS.md').read_text()
        self.assertIn('Real shared-world event: NOT_TESTED',status)
        self.assertIn('Original game data: BLOCKED',status)

if __name__=='__main__': unittest.main()
