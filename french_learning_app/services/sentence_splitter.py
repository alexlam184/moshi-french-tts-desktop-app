import re


def split_sentences(text: str) -> list[str]:
    """Split French prose conservatively while retaining terminal punctuation."""
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []
    pieces = re.split(r"(?<=[.!?…])\s+(?=[A-ZÀÂÇÉÈÊËÎÏÔÙÛÜŸŒ])", normalized)
    return [piece.strip() for piece in pieces if piece.strip()]
