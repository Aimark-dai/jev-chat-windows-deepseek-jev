import unittest

import numpy as np

from app.ocr import Reader


def _box(left, top, right, bottom):
    return [(left, top), (right, top), (right, bottom), (left, bottom)]


class QuoteReaderTests(unittest.TestCase):
    def test_group_reply_keeps_quoted_image_owner_separate_from_sender(self):
        frame = np.full((150, 230, 3), 35, dtype=np.uint8)
        frame[43:71, 35:165] = 50
        frame[52:57, 55:125] = 255
        frame[83:88, 50:120] = 125
        ocr_lines = [
            (_box(20, 15, 45, 30), "X", 0.99),
            (_box(45, 46, 150, 67), "这个", 0.99),
            (_box(48, 77, 135, 98), "成员乙:", 0.99),
        ]
        reader = Reader.__new__(Reader)
        reader.ocr = lambda *_args, **_kwargs: (ocr_lines, None)
        reader.lh = None
        reader.seen = []

        lines = reader.read(frame, np.array([35, 35, 35], dtype=np.uint8))

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0][:2], ("her", "X"))
        self.assertIn("引用：成员乙", lines[0][2])
        self.assertIn("内容未完整识别", lines[0][2])
        self.assertNotIn("me", str(lines))


if __name__ == "__main__":
    unittest.main()
