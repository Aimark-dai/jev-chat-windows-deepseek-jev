import unittest

from app import jev_display


class JevDisplayTests(unittest.TestCase):
    def test_formats_official_typesafe_score_fields_without_rounding_conflict(self):
        item = {
            "type": "score",
            "score": 2.82,
            "confidence": 0.53,
            "probabilities": {str(i): value for i, value in enumerate(
                [0.0, 0.15, 0.28, 0.17, 0.4, 0.0, 0.0, 0.0, 0.0, 0.0]
            )},
        }

        self.assertEqual(jev_display.danger_summary(item), "危险 2.8/9 · 把握 53%")
        self.assertEqual(jev_display.high_risk_probability(item), 0.0)

    def test_formats_choice_confidence_and_top_probabilities(self):
        item = {
            "type": "choice",
            "choice": "confirm_you_care",
            "confidence": 0.56,
            "probabilities": {
                "confirm_you_care": 0.63,
                "casual_chat": 0.14,
                "close_topic": 0.11,
                "vent_anger": 0.08,
            },
        }

        self.assertEqual(
            jev_display.choice_summary("true_intent", item),
            "希望确认你在意 · 把握 56%",
        )
        self.assertEqual(
            jev_display.choice_distribution("true_intent", item),
            "意图概率：希望确认你在意 63% · 轻松交流 14%",
        )

    def test_formats_noul_and_score_probabilities(self):
        answers = {
            "literal_question": {"type": "noul", "noul": 0.12},
            "should_reply_now": {"type": "noul", "noul": 0.31},
            "tension_resolved": {"type": "noul", "noul": 0.17},
            "danger_level": {
                "type": "score",
                "score": 2.82,
                "confidence": 0.53,
                "probabilities": {"5": 0.05, "6": 0.07, "7": 0.03, "8": 0.01, "9": 0.0},
            },
        }

        self.assertEqual(
            jev_display.probability_summary(answers),
            "字面理解 12% · 实质内容 31% · 紧张缓解 17% · 高风险 11%",
        )


if __name__ == "__main__":
    unittest.main()
