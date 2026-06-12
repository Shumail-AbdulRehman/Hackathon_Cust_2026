"""Text normalization utilities for Pakistani civic records.

The functions here are deliberately conservative. They normalize noisy text
without using identity-specific lookup tables.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher


HONORIFICS_ALWAYS = {
    "mr",
    "mrs",
    "ms",
    "miss",
    "dr",
    "haji",
    "syed",
    "sayed",
}

LEADING_TITLES = {
    "ch",
    "chaudhry",
    "chaudhary",
    "malik",
    "mian",
    "raja",
    "sardar",
}

NAME_ALIASES = {
    "mohd": "muhammad",
    "mhd": "muhammad",
    "muhd": "muhammad",
    "mohamad": "muhammad",
    "mohammad": "muhammad",
    "muhamad": "muhammad",
    "muhammed": "muhammad",
    "mohammed": "muhammad",
    "mhmd": "muhammad",
    "mhmmd": "muhammad",
    "ahmd": "ahmed",
    "hmad": "ahmed",
    "aly": "ali",
    "rsa": "raza",
    "rza": "raza",
    "asman": "usman",
    "athman": "usman",
    "asmat": "usman",
    "tarq": "tariq",
    "tark": "tariq",
    "sara": "sara",
    "sarh": "sara",
    "mlk": "malik",
    "abdul": "abdul",
    "abd": "abdul",
}

TOKEN_EQUIVALENTS = {
    "m": {"m", "muhammad"},
    "muhammad": {"muhammad", "m"},
    "ahmad": {"ahmad", "ahmed"},
    "ahmed": {"ahmed", "ahmad"},
}

ADDRESS_WORDS = {
    "road": "rd",
    "street": "st",
    "sector": "sec",
    "phase": "ph",
    "house": "h",
    "flat": "flt",
    "block": "blk",
    "apartment": "apt",
    "avenue": "ave",
    "mohalla": "moh",
    "colony": "col",
}

URDU_ARABIC_APPROX = {
    "ا": "a",
    "آ": "a",
    "ب": "b",
    "پ": "p",
    "ت": "t",
    "ٹ": "t",
    "ث": "s",
    "ج": "j",
    "چ": "ch",
    "ح": "h",
    "خ": "kh",
    "د": "d",
    "ڈ": "d",
    "ذ": "z",
    "ر": "r",
    "ڑ": "r",
    "ز": "z",
    "ژ": "zh",
    "س": "s",
    "ش": "sh",
    "ص": "s",
    "ض": "z",
    "ط": "t",
    "ظ": "z",
    "ع": "a",
    "غ": "gh",
    "ف": "f",
    "ق": "q",
    "ک": "k",
    "گ": "g",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ں": "n",
    "و": "w",
    "ہ": "h",
    "ھ": "h",
    "ء": "",
    "ی": "y",
    "ے": "e",
}


def transliterate_urdu(text: str) -> str:
    return "".join(URDU_ARABIC_APPROX.get(char, char) for char in text)


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = transliterate_urdu(text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s./-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_name_tokens(value: object) -> list[str]:
    text = normalize_text(value)
    tokens = []
    raw_tokens = text.replace(".", " ").split()
    for index, raw in enumerate(raw_tokens):
        token = raw.strip("-/")
        if not token:
            continue
        if token in HONORIFICS_ALWAYS:
            continue
        if index == 0 and token in LEADING_TITLES:
            continue
        token = NAME_ALIASES.get(token, token)
        tokens.append(token)
    return tokens


def normalize_name(value: object) -> str:
    tokens = normalize_name_tokens(value)
    return " ".join(tokens)


def normalize_address(value: object) -> str:
    text = normalize_text(value)
    tokens = []
    for raw in re.split(r"[\s,]+", text):
        token = raw.strip()
        if not token:
            continue
        tokens.append(ADDRESS_WORDS.get(token, token))
    return " ".join(tokens)


def normalize_phone(value: object) -> str:
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if digits.startswith("92") and len(digits) >= 12:
        digits = "0" + digits[2:]
    return digits[-11:] if len(digits) >= 11 else digits


def normalize_national_id(value: object) -> str:
    """Normalize a national identifier to a clean digit string.

    CNIC: 13 digits (XXXXX-XXXXXXX-X).
    NTN: 7 digits.
    Any other digit-only identifier with 5+ digits is also accepted so that
    external datasets (e.g., ICIJ node IDs) can be used as exact-match keys.
    Returns empty string if it does not look like an identifier.
    """
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) >= 5:
        return digits
    return ""


def token_set(text: str) -> set[str]:
    return {token for token in normalize_name_tokens(text) if token}


def alias_token_set(text: str) -> set[str]:
    tokens = set()
    for token in normalize_name_tokens(text):
        tokens.update(TOKEN_EQUIVALENTS.get(token, {token}))
    return tokens


def initials(text: str) -> str:
    return "".join(token[0] for token in normalize_name_tokens(text) if token)


def first_initial(text: str) -> str:
    tokens = normalize_name_tokens(text)
    return tokens[0][0] if tokens else ""


def surname(text: str) -> str:
    tokens = normalize_name_tokens(text)
    return tokens[-1] if tokens else ""


def sequence_score(left: str, right: str) -> float:
    left_n = normalize_text(left)
    right_n = normalize_text(right)
    if not left_n or not right_n:
        return 0.0
    return SequenceMatcher(None, left_n, right_n).ratio()


def cosine_score(left_counts: Counter[str], right_counts: Counter[str]) -> float:
    if not left_counts or not right_counts:
        return 0.0
    intersection = set(left_counts) & set(right_counts)
    numerator = sum(left_counts[token] * right_counts[token] for token in intersection)
    left_norm = sum(value * value for value in left_counts.values()) ** 0.5
    right_norm = sum(value * value for value in right_counts.values()) ** 0.5
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def char_ngrams(text: str, n: int = 3) -> Counter[str]:
    compact = re.sub(r"\s+", " ", normalize_text(text)).strip()
    if not compact:
        return Counter()
    padded = f"  {compact}  "
    return Counter(padded[index : index + n] for index in range(max(len(padded) - n + 1, 0)))


def ngram_embedding_similarity(left: str, right: str) -> float:
    """Standard-library character n-gram cosine similarity.

    This is not a neural embedding, but it gives the prototype a transparent
    semantic-like feature that handles transliteration and spelling drift.
    """

    return cosine_score(char_ngrams(left), char_ngrams(right))


def phonetic_code(token: str) -> str:
    token = NAME_ALIASES.get(normalize_text(token), normalize_text(token))
    if not token:
        return ""
    replacements = str.maketrans({"q": "k", "c": "k", "x": "ks", "z": "s", "v": "w"})
    token = token.translate(replacements)
    first = token[0]
    tail = re.sub(r"[aeiouhwy]", "", token[1:])
    collapsed = []
    for char in first + tail:
        if not collapsed or collapsed[-1] != char:
            collapsed.append(char)
    return "".join(collapsed)


def phonetic_similarity(left: str, right: str) -> float:
    left_codes = {phonetic_code(token) for token in normalize_name_tokens(left)}
    right_codes = {phonetic_code(token) for token in normalize_name_tokens(right)}
    left_codes.discard("")
    right_codes.discard("")
    if not left_codes or not right_codes:
        return 0.0
    inter = len(left_codes & right_codes)
    union = len(left_codes | right_codes)
    return inter / union if union else 0.0


def token_similarity(left: str, right: str) -> float:
    left_tokens = alias_token_set(left)
    right_tokens = alias_token_set(right)
    if not left_tokens or not right_tokens:
        return 0.0
    inter = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    jaccard = inter / union if union else 0.0
    seq = sequence_score(" ".join(sorted(left_tokens)), " ".join(sorted(right_tokens)))
    phonetic = phonetic_similarity(left, right)
    embedding = ngram_embedding_similarity(left, right)
    return max(jaccard, seq, phonetic * 0.92, embedding * 0.9)


def initials_compatible(left: str, right: str) -> bool:
    left_initials = initials(left)
    right_initials = initials(right)
    if not left_initials or not right_initials:
        return False
    if left_initials.startswith(right_initials) or right_initials.startswith(left_initials):
        return True
    same_surname = bool(surname(left) and surname(left) == surname(right))
    return same_surname and first_initial(left) == first_initial(right)


def address_block(value: object) -> str:
    text = normalize_address(value)
    tokens = text.split()
    useful = [token for token in tokens if any(ch.isdigit() for ch in token) or len(token) > 2]
    return " ".join(useful[:4])


def city_hint(value: object) -> str:
    text = normalize_address(value)
    for city in ("karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "multan", "peshawar", "quetta"):
        if city in text:
            return city
    tokens = text.split()
    return tokens[-1] if tokens else ""
