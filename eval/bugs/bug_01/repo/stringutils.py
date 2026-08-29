"""Small string utility helpers."""


def truncate(text, length):
    """Return at most ``length`` characters of ``text``.

    If ``text`` is longer than ``length`` it is cut down to fit; otherwise it
    is returned unchanged.
    """
    if len(text) <= length:
        return text
    return text[:length - 1]


def word_count(text):
    """Return the number of whitespace-separated words in ``text``."""
    return len(text.split())


def normalize_spaces(text):
    """Collapse runs of whitespace into single spaces and strip the ends."""
    return " ".join(text.split())


def initials(name):
    """Return the uppercased first letter of each word in ``name``."""
    return "".join(word[0].upper() for word in name.split() if word)
