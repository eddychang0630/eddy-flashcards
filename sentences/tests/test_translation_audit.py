import unittest

from sentences.translation_audit import approve_reviews, build_request, fingerprint, pending_reviews, require_reviewed


class TranslationAuditTest(unittest.TestCase):
    def setUp(self):
        self.cards = [{
            "id": "class-20260907-01", "type": "class", "prompt_zh": "我又要過學生生活了。",
            "question_en": "", "answer_en": "I'll be a student again.", "answer_zh": "我又要過學生生活了。",
        }]

    def test_new_or_changed_translation_requires_review(self):
        ledger = {"schema_version": 1, "cards": {}}
        self.assertEqual(1, len(pending_reviews(self.cards, ledger)))
        request = build_request(self.cards, ledger)
        approved = approve_reviews(self.cards, ledger, {"reviews": [{"id": request["cards"][0]["id"], "fingerprint": request["cards"][0]["fingerprint"], "approved": True}]})
        self.assertEqual([], pending_reviews(self.cards, approved))
        changed = [{**self.cards[0], "answer_zh": "錯誤翻譯"}]
        self.assertEqual(1, len(pending_reviews(changed, approved)))

    def test_stale_or_unapproved_response_cannot_change_ledger(self):
        ledger = {"schema_version": 1, "cards": {}}
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            approve_reviews(self.cards, ledger, {"reviews": [{"id": self.cards[0]["id"], "fingerprint": "old", "approved": True}]})
        with self.assertRaisesRegex(ValueError, "approved"):
            approve_reviews(self.cards, ledger, {"reviews": [{"id": self.cards[0]["id"], "fingerprint": fingerprint(self.cards[0]), "approved": False}]})

    def test_publication_is_blocked_until_every_current_card_is_reviewed(self):
        with self.assertRaisesRegex(ValueError, "class-20260907-01"):
            require_reviewed(self.cards, {"schema_version": 1, "cards": {}})
        approved = {"schema_version": 1, "cards": {self.cards[0]["id"]: fingerprint(self.cards[0])}}
        require_reviewed(self.cards, approved)


if __name__ == "__main__":
    unittest.main()
