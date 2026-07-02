"""
test_arabizi_transliterator.py — Test suite for the Arabizi transliterator.

Covers:
  - Authority contract & B-prime isolation
  - Feature flag / sparse activation
  - Detection: pure Arabic, pure English → ~0 confidence
  - Detection: clear Arabizi → high confidence
  - Transliteration accuracy (harm-relevant + safe words)
  - Mixed Arabizi + English detection
  - Maghrebi dialect patterns
  - Edge cases: numbers-that-aren't-Arabizi, URLs, emails, empty input
  - ArabiziResult shape & immutability
  - Determinism

License: BSL 1.1
Architect: Abdulmjeed Ibrahim Khenkar
Co-builder: Claude (Anthropic)
"""

import pytest

from engine.aatif_arabizi_transliterator import (
    ARABIZI_ENABLED,
    DETECT_THRESHOLD,
    TOKEN_ARABIZI_THRESHOLD,
    ArabiziResult,
    ArabiziTransliterator,
    is_arabizi,
    process,
    transliterate,
    transliterate_token,
)


@pytest.fixture
def tr():
    return ArabiziTransliterator()


def _is_arabic_script(s: str) -> bool:
    """True if the string contains at least one Arabic-script character."""
    return any("؀" <= c <= "ۿ" for c in s)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Authority contract & B-prime isolation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestAuthorityContract:
    def test_authority_level(self):
        assert ArabiziTransliterator.AUTHORITY_LEVEL == "B_PRIME_OBSERVATIONAL"

    def test_cannot_block_runtime(self):
        assert ArabiziTransliterator.CAN_BLOCK_RUNTIME is False

    def test_cannot_modify_h(self):
        assert ArabiziTransliterator.CAN_MODIFY_H is False

    def test_cannot_modify_theta(self):
        assert ArabiziTransliterator.CAN_MODIFY_THETA is False

    def test_cannot_modify_s(self):
        assert ArabiziTransliterator.CAN_MODIFY_S is False

    def test_cannot_emit_judicial_decision(self):
        assert ArabiziTransliterator.CAN_EMIT_JUDICIAL_DECISION is False

    def test_binding_channel(self):
        assert ArabiziTransliterator.BINDING_CHANNEL == "B1"

    def test_isolation_marker(self):
        assert "NOT_FOR_SAFETY" in ArabiziTransliterator.ISOLATION_MARKER

    def test_result_isolation_marker(self):
        r = process("9tl")
        assert "NOT_FOR_SAFETY" in r._isolation_marker


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Detection — negatives (pure Arabic / pure English)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDetectionNegatives:
    def test_pure_arabic_not_arabizi(self, tr):
        # Already Arabic script — nothing to transliterate.
        assert tr.is_arabizi("أريد أن أقتل الوقت") == 0.0

    def test_pure_arabic_short(self, tr):
        assert tr.is_arabizi("قتل حرق سم") == 0.0

    def test_pure_english_sentence(self, tr):
        assert tr.is_arabizi("hello how are you doing today") == 0.0

    def test_pure_english_single_word(self, tr):
        assert tr.is_arabizi("everything") == 0.0

    def test_english_chat_abbreviations(self, tr):
        # lol / omg / btw are chat noise, not Arabizi.
        assert tr.is_arabizi("lol omg btw idk") == 0.0

    def test_empty_string(self, tr):
        assert tr.is_arabizi("") == 0.0

    def test_whitespace_only(self, tr):
        assert tr.is_arabizi("   ") == 0.0

    def test_below_min_length(self, tr):
        assert tr.is_arabizi("a") == 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Detection — positives (clear Arabizi)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDetectionPositives:
    def test_harm_word_9tl(self, tr):
        assert tr.is_arabizi("9tl") >= 0.7

    def test_harm_word_7rg(self, tr):
        assert tr.is_arabizi("7rg") >= 0.7

    def test_clear_arabizi_sentence(self, tr):
        conf = tr.is_arabizi("ya 7abibi ana 3ayez aro7 el bet")
        assert conf >= 0.8

    def test_safe_arabizi_3adi(self, tr):
        assert tr.is_arabizi("3adi") >= 0.7

    def test_flag_set_when_confident(self, tr):
        r = tr.process("ya 7abibi 3ala keteer")
        assert r.is_arabizi is True
        assert r.confidence >= DETECT_THRESHOLD

    def test_consonant_skeleton_detected(self, tr):
        # No digits, but a pure consonant cluster still reads as Arabizi.
        assert tr.is_arabizi("mkhdr") >= TOKEN_ARABIZI_THRESHOLD


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Transliteration — harm-relevant words (exact skeleton)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestHarmTransliteration:
    @pytest.mark.parametrize("arabizi,arabic", [
        ("9tl", "قتل"),     # kill
        ("7rg", "حرق"),     # burn
        ("sm", "سم"),       # poison
        ("mkhdr", "مخدر"),  # drugs
    ])
    def test_harm_words_exact(self, tr, arabizi, arabic):
        assert tr.transliterate(arabizi) == arabic

    def test_harm_word_in_sentence(self, tr):
        # The harm token is surfaced in Arabic even amid other text.
        out = tr.transliterate("ana 3ayez a9tl")
        assert "قتل" in out


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. Transliteration — safe words
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestSafeTransliteration:
    def test_3adi_exact(self, tr):
        assert tr.transliterate("3adi") == "عادي"

    def test_7abibi_skeleton(self, tr):
        # Vowel placement is approximate; the consonant skeleton must land.
        out = tr.transliterate("7abibi")
        assert _is_arabic_script(out)
        assert out.startswith("ح")
        assert "ب" in out and "ي" in out

    def test_shukran_skeleton(self, tr):
        out = tr.transliterate("shukran")
        assert _is_arabic_script(out)
        assert out.startswith("ش")
        assert "ك" in out and "ر" in out

    def test_known_word_ya(self, tr):
        assert tr.transliterate("ya") == "يا"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6. Digit & digraph mappings
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMappings:
    @pytest.mark.parametrize("token,expected", [
        ("3", "ع"),
        ("7", "ح"),
        ("5", "خ"),
        ("6", "ط"),
        ("2", "ء"),
        ("8", "ق"),
        ("9", "ق"),
    ])
    def test_single_digit_map(self, token, expected):
        assert transliterate_token(token) == expected

    @pytest.mark.parametrize("token,expected", [
        ("3'", "غ"),   # ghayn
        ("7'", "خ"),   # khaa variant
        ("6'", "ظ"),   # zaa
        ("9'", "ض"),   # daad
    ])
    def test_dotted_digit_map(self, token, expected):
        assert transliterate_token(token) == expected

    @pytest.mark.parametrize("token,expected", [
        ("kh", "خ"),
        ("gh", "غ"),
        ("sh", "ش"),
        ("ch", "ش"),
        ("th", "ث"),
        ("dh", "ذ"),
    ])
    def test_digraph_map(self, token, expected):
        assert transliterate_token(token) == expected

    def test_digraph_beats_single_letters(self):
        # "kh" must map to خ, not to ك + ه.
        assert transliterate_token("kh") == "خ"
        assert transliterate_token("kh") != "كه"

    def test_dotted_digit_beats_bare_digit(self):
        # "3'" must map to غ, not ع + apostrophe.
        assert transliterate_token("3'") == "غ"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  7. Mixed text
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMixedText:
    def test_mixed_arabizi_english_detected(self, tr):
        conf = tr.is_arabizi("let's meet 3ala el maw3ed bokra")
        assert conf >= DETECT_THRESHOLD

    def test_mixed_preserves_english_token(self, tr):
        # Plain English words are left in Latin; Arabizi is transliterated.
        out = tr.transliterate("meeting 3ala 8pm")
        assert "meeting" in out
        assert _is_arabic_script(out)

    def test_mixed_transliterates_arabizi_part(self, tr):
        out = tr.transliterate("call me 3ala el mobile")
        assert "call" in out          # plain English preserved
        assert "ع" in out             # 3ala → عالا (ayn surfaced)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  8. Maghrebi dialect patterns
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestMaghrebi:
    def test_wesh_rak(self, tr):
        # "wesh rak" — Maghrebi "how are you".
        assert tr.is_arabizi("wesh rak sa7bi") >= DETECT_THRESHOLD

    def test_maghrebi_9_is_qaf(self, tr):
        # Maghrebi reads 9 as ق. "9lb" (vowels dropped) → قلب (heart).
        assert tr.transliterate("9lb") == "قلب"
        # "9alb" writes the short vowel, so it renders as قالب — 9 is still ق.
        assert tr.transliterate("9alb").startswith("قا")

    def test_bzaf(self, tr):
        # "bzaf" / "bezaf" — Maghrebi "a lot".
        assert tr.is_arabizi("bezaf") >= TOKEN_ARABIZI_THRESHOLD

    def test_maghrebi_harm_9tl(self, tr):
        # The security-critical Maghrebi reading.
        assert tr.transliterate("bghit n9tl") .endswith("قتل") or \
            "قتل" in tr.transliterate("bghit n9tl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  9. Edge cases
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestEdgeCases:
    def test_plain_number_not_arabizi(self, tr):
        # A bare number is not an Arabizi substitution.
        assert tr.is_arabizi("the year 2024 was great") == 0.0

    def test_phone_number_not_arabizi(self, tr):
        assert tr.is_arabizi("call 911 now") == 0.0

    def test_url_stripped(self, tr):
        assert tr.is_arabizi("visit https://example.com/page7 today") == 0.0

    def test_email_stripped(self, tr):
        assert tr.is_arabizi("email me at user7@test.com") == 0.0

    def test_tech_token_not_arabizi(self, tr):
        assert tr.is_arabizi("play the mp3 file") == 0.0

    def test_none_safe_in_process(self, tr):
        r = tr.process(None)
        assert r.original == ""
        assert r.is_arabizi is False

    def test_transliterate_empty(self, tr):
        assert tr.transliterate("") == ""

    def test_arabic_passthrough_transliterate(self, tr):
        # Arabic script is not transliterated (already Arabic).
        text = "قتل حرق"
        assert tr.transliterate(text) == text

    def test_english_passthrough_transliterate(self, tr):
        assert tr.transliterate("hello world") == "hello world"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  10. ArabiziResult shape & immutability
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestResult:
    def test_result_fields(self, tr):
        r = tr.process("9tl")
        assert isinstance(r, ArabiziResult)
        assert isinstance(r.is_arabizi, bool)
        assert isinstance(r.confidence, float)
        assert r.original == "9tl"
        assert r.transliterated == "قتل"

    def test_result_frozen(self, tr):
        r = tr.process("9tl")
        with pytest.raises(Exception):
            r.confidence = 0.0  # type: ignore[misc]

    def test_confidence_in_range(self, tr):
        for s in ["9tl", "hello", "3adi", "قتل", "", "mp3 file"]:
            c = tr.is_arabizi(s)
            assert 0.0 <= c <= 1.0

    def test_original_preserved(self, tr):
        src = "ya 7abibi"
        assert tr.process(src).original == src


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  11. Determinism & module-level API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestDeterminismAndApi:
    def test_deterministic_detection(self, tr):
        s = "ya 7abibi ana 3ayez a9tl"
        assert tr.is_arabizi(s) == tr.is_arabizi(s)

    def test_deterministic_transliteration(self, tr):
        s = "9tl 7rg sm mkhdr"
        assert tr.transliterate(s) == tr.transliterate(s)

    def test_module_functions_match_class(self, tr):
        s = "ya 7abibi 3adi"
        assert is_arabizi(s) == tr.is_arabizi(s)
        assert transliterate(s) == tr.transliterate(s)
        assert process(s).transliterated == tr.process(s).transliterated

    def test_feature_flag_present(self):
        assert isinstance(ARABIZI_ENABLED, bool)
