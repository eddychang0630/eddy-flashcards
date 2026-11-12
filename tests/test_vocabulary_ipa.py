import unittest

from vocabulary_ipa import add_pronunciations, format_ipa, pronunciation_requests


class VocabularyIPATest(unittest.TestCase):
    def test_stress_is_placed_before_the_syllable_onset(self):
        self.assertEqual("/haɪˈdʒiːnɪk/", format_ipa("haɪdʒˈiːnɪk"))
        self.assertEqual("/kəmˈpleɪn/", format_ipa("kəmplˈeɪn"))
        self.assertEqual("/skɛɹs/", format_ipa("skˈɛɹs"))

    def test_only_single_words_request_ipa(self):
        cards = [
            ["scarce", "", "adj."],
            ["hygienic", "", "adj."],
            ["check in", "", "phrasal verb"],
            ["bumper-to-bumper", "", "adj. phrase"],
            ["time-conscious", "", "adj."],
            ["take\toff", "", "v."],
            ["whatever", "", "口語表達"],
        ]
        self.assertEqual(
            [("scarce", "adj."), ("hygienic", "adj."), ("time-conscious", "adj.")],
            pronunciation_requests(cards),
        )

    def test_cards_keep_their_other_fields_and_phrases_have_no_ipa(self):
        cards = [
            ["scarce", "", "adj.", "稀少的"],
            ["check in", "/old/", "phrasal verb", "辦理入住"],
            ["scarce", "", "adj.", "缺乏的"],
        ]
        add_pronunciations(cards, {("scarce", "adj."): "/skɛɹs/"})
        self.assertEqual(
            [
                ["scarce", "/skɛɹs/", "adj.", "稀少的"],
                ["check in", "", "phrasal verb", "辦理入住"],
                ["scarce", "/skɛɹs/", "adj.", "缺乏的"],
            ],
            cards,
        )
