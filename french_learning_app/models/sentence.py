from dataclasses import dataclass


@dataclass(frozen=True)
class Sentence:
    french: str
    translation: str = "Translation unavailable — connect a translation provider later."
    ipa: str = "IPA unavailable — connect an IPA provider later."
