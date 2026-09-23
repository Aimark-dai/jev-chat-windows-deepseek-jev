import unittest

from app.ocr import Reader


def line(who, text, y, name=None):
    return who, name, text, y


class MessageDedupTests(unittest.TestCase):
    def setUp(self):
        self.reader = Reader.__new__(Reader)
        self.reader.seen = []

    def test_similar_short_reply_cannot_hide_new_group_message_above_it(self):
        old = [line("her", "还有一项资料要核对", 100, "群友甲"), line("me", "好呀", 200)]
        self.reader.new_lines(old)

        current = old + [line("her", "我只看到两项，还缺哪项", 300, "群友乙"),
                         line("me", "好吧", 400)]
        self.assertEqual(self.reader.new_lines(current),
                         [("her", "群友乙", "我只看到两项，还缺哪项"),
                          ("me", None, "好吧")])
        self.assertEqual(self.reader.new_lines(current), [])

    def test_same_short_text_sent_again_is_new_message(self):
        old = [line("her", "好的", 100, "群友甲")]
        self.reader.new_lines(old)
        self.assertEqual(self.reader.new_lines(old + [line("her", "好的", 200, "群友甲")]),
                         [("her", "群友甲", "好的")])

    def test_scrolling_up_does_not_report_older_messages_as_new(self):
        old = [line("her", "第一条原有消息", 100, "甲"),
               line("her", "第二条原有消息", 200, "乙"),
               line("me", "第三条原有消息", 300)]
        self.reader.new_lines(old)
        current = [line("her", "更早的消息", 100, "丙"), old[0], old[1]]
        self.assertEqual(self.reader.new_lines(current), [])

    def test_unchanged_view_and_long_ocr_jitter_do_not_repeat(self):
        old = [line("her", "这是一条比较长的原有消息", 100, "甲")]
        self.assertEqual(len(self.reader.new_lines(old)), 1)
        jittered = [line("her", "这是一条比较长的原右消息", 100, "甲")]
        self.assertEqual(self.reader.new_lines(jittered), [])


if __name__ == "__main__":
    unittest.main()
