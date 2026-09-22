import unittest

from core import draft


class DeepSeekDraftTests(unittest.TestCase):
    def test_openrouter_provider_is_rejected(self):
        with self.assertRaisesRegex(draft.JevError, "只支持 DeepSeek"):
            draft.draft_candidates([("her", "在吗")], "friends", provider="openrouter")


if __name__ == "__main__":
    unittest.main()
