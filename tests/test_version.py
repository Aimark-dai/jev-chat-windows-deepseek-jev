import subprocess
import unittest
from unittest.mock import patch

from app import version


class VersionTest(unittest.TestCase):
    def test_source_version_uses_latest_git_tag(self):
        completed = subprocess.CompletedProcess([], 0, stdout="v1.2.3\n", stderr="")
        with patch("app.version.subprocess.run", return_value=completed):
            self.assertEqual(version._source_version(), "1.2.3-dev")

    def test_source_version_falls_back_without_git(self):
        with patch("app.version.subprocess.run", side_effect=OSError("git unavailable")):
            self.assertEqual(version._source_version(), "0.0.0-dev")


if __name__ == "__main__":
    unittest.main()
