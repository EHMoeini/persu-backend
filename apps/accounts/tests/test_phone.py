from django.test import SimpleTestCase

from apps.accounts.phone import InvalidPhoneNumber, mask_phone, normalize_phone


class NormalizePhoneTests(SimpleTestCase):
    def test_normalizes_national_number_with_iso_region(self):
        self.assertEqual(
            normalize_phone("US", "(202) 456-1111"), "+12024561111"
        )

    def test_normalizes_with_dialing_code(self):
        self.assertEqual(normalize_phone("1", "2024561111"), "+12024561111")

    def test_normalizes_with_plus_prefixed_dialing_code(self):
        self.assertEqual(normalize_phone("+1", "202-456-1111"), "+12024561111")

    def test_accepts_already_international_number(self):
        self.assertEqual(
            normalize_phone("US", "+44 20 7183 8750"), "+442071838750"
        )

    def test_accepts_lowercase_iso_region(self):
        self.assertEqual(
            normalize_phone("gb", "020 7183 8750"), "+442071838750"
        )

    def test_rejects_missing_number(self):
        with self.assertRaises(InvalidPhoneNumber):
            normalize_phone("US", "")

    def test_rejects_invalid_number(self):
        with self.assertRaises(InvalidPhoneNumber):
            normalize_phone("US", "12345")

    def test_rejects_number_without_country_context(self):
        with self.assertRaises(InvalidPhoneNumber):
            normalize_phone("", "2024561111")

    def test_rejects_unknown_country_code_format(self):
        with self.assertRaises(InvalidPhoneNumber):
            normalize_phone("USA!", "2024561111")


class MaskPhoneTests(SimpleTestCase):
    def test_masks_all_but_last_four_digits(self):
        self.assertEqual(mask_phone("+12024561111"), "***1111")

    def test_handles_empty_value(self):
        self.assertEqual(mask_phone(""), "***")
