"""Smoke test for historical-run batch CLI."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from scripts.build_history import main


class BuildHistoryCLITests(unittest.TestCase):
    def test_batch_creates_distinct_json_files(self):
        with TemporaryDirectory() as folder:
            self.assertEqual(main(["--start", "4", "--end", "5", "--repeats", "2",
                                   "--algorithms", "stack_backtracking", "--history-dir", folder]), 0)
            files = sorted(Path(folder).glob("**/*.json"))
            self.assertEqual(len(files), 4)
            records = [json.loads(f.read_text(encoding="utf-8")) for f in files]
            self.assertCountEqual([r["n"] for r in records], [4, 4, 5, 5])
            self.assertTrue(all(r["finished"] and not r["step_visualization_enabled"] for r in records))


if __name__ == "__main__":
    unittest.main()
