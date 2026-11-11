"""Run the original fourteen assertion methods against the offline candidate."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
spec = importlib.util.spec_from_file_location('hourly_original_tests',
    REPO / 'infra/penpot/runtime/health-supervision/test_supervisor.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
spec = importlib.util.spec_from_file_location('hourly_original_candidate', ROOT / 'candidate/supervisor.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
original.s = candidate

# Adapt only the shared fixture to the newly required DNS reaper policy; the
# original fourteen test methods and all their assertions remain untouched.
original_fixture = original.fixture

def fixture_with_DNS_init():
    lock, frame = original_fixture()
    lock['services']['penpot-dns']['require_init'] = True
    frame['penpot-dns']['init'] = True
    return lock, frame

original.fixture = fixture_with_DNS_init


class OriginalContracts(unittest.TestSuite):
    def run(self, result, debug=False):
        # All original assertions stay unchanged. Only the new diagnostic sink is
        # mocked so those historical tests cannot write the production ledger path.
        with patch.object(candidate, 'record_failure'):
            return super().run(result, debug)


def load_tests(loader, tests, pattern):
    return OriginalContracts(loader.loadTestsFromModule(original))
