"""Fabricated-only tests for restricted Golf two-sprintf literal roles."""
from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_p0_golf_two_sprintf_literal_roles_private as role


def payload(text: bytes) -> bytes:
    return (text + b"\x00" * role.fmt.MAX_TEXT)[:role.fmt.MAX_TEXT]


class LiteralRoleTests(unittest.TestCase):
    def test_one_int_distance_unit(self):
        r = role.classify_literal_bytes(payload(b"%d ft\x00"))
        self.assertTrue(r["explicit_distance_unit_token"])
        self.assertFalse(r["no_recognized_role_tokens"])
        self.assertFalse(r["literal_content_exposed"])
        self.assertFalse(r["source_message_semantics_verified"])

    def test_nearpin_and_yard(self):
        r = role.classify_literal_bytes(payload(b"near pin: %u yards\x00"))
        self.assertTrue(r["distance_or_target_token"])
        self.assertTrue(r["explicit_distance_unit_token"])

    def test_result_word(self):
        r = role.classify_literal_bytes(payload(b"Result %i\x00"))
        self.assertTrue(r["result_screen_word_token"])

    def test_score_context(self):
        r = role.classify_literal_bytes(payload(b"Score:%03d\x00"))
        self.assertTrue(r["score_or_stroke_token"])
        self.assertFalse(r["explicit_distance_unit_token"])

    def test_timer_and_debug(self):
        r = role.classify_literal_bytes(payload(b"debug timer %d ms\x00"))
        self.assertTrue(r["timer_token"])
        self.assertTrue(r["debug_or_counter_token"])

    def test_only_integer_no_context_remains_unknown(self):
        r = role.classify_literal_bytes(payload(b"%d\x00"))
        self.assertTrue(r["no_recognized_role_tokens"])
        self.assertFalse(r["explicit_distance_unit_token"])

    def test_hex_arg_is_integer_format(self):
        r = role.classify_literal_bytes(payload(b"trace 0x%x\x00"))
        self.assertTrue(r["debug_or_counter_token"])

    def test_floating_only_rejected(self):
        self.assertEqual(role.classify_literal_bytes(payload(b"%.2f ft\x00"))
                         ["status"], "unqualified_non_single_int_format")

    def test_multiple_ints_rejected(self):
        self.assertEqual(role.classify_literal_bytes(payload(b"%d of %d\x00"))
                         ["status"], "unqualified_non_single_int_format")

    def test_percent_n_rejected(self):
        self.assertEqual(role.classify_literal_bytes(payload(b"%n\x00"))
                         ["status"], "unqualified_non_single_int_format")

    def test_nonterminated_rejected(self):
        self.assertEqual(role.classify_literal_bytes(b"A" * role.fmt.MAX_TEXT)
                         ["status"], "unqualified_not_nul_terminated")

    def test_nonascii_rejected(self):
        self.assertEqual(role.classify_literal_bytes(payload(b"\xff %d\x00"))
                         ["status"], "unqualified_non_ascii")

    def test_empty_string_rejected(self):
        self.assertEqual(role.classify_literal_bytes(payload(b"\x00"))
                         ["status"], "unqualified_not_nul_terminated")

    def test_bad_size_abstains(self):
        with self.assertRaises(role.base.UntrustedInput):
            role.classify_literal_bytes(b"\x00" * 12)

    def test_escaped_percent_does_not_create_second_conversion(self):
        r = role.classify_literal_bytes(payload(b"%% then %d\x00"))
        self.assertEqual(r["status"],
                         "one_integer_printf_conversion_context_classified")
        self.assertTrue(r["no_recognized_role_tokens"])

    def test_category_never_leaks_original_literal_or_private_address(self):
        src = b"near target 22 yards %d\x00"
        result = role.classify_literal_bytes(payload(src))
        report = json.dumps(result)
        self.assertNotIn("near target", report)
        self.assertNotIn("22 yards", report)
        self.assertNotIn("8040", report)
        self.assertTrue(result["explicit_distance_unit_token"])

    def test_help_import_safe_without_private_archive(self):
        script = Path(role.__file__).resolve()
        proc = subprocess.run(
            [sys.executable, "-I", str(script), "--help"],
            capture_output=True, text=True, cwd=script.parents[2],
            timeout=12,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--baseline", proc.stdout)


if __name__ == "__main__":
    unittest.main()
