"""RFID helpers for the simulated console reader."""

from __future__ import annotations


def normalize_uid(value: str) -> str:
    """Normalize a manually typed RFID/NFC UID to uppercase hexadecimal text."""

    normalized = value.strip().upper()
    for separator in (" ", ":", "-", "_"):
        normalized = normalized.replace(separator, "")
    if normalized.startswith("0X"):
        normalized = normalized[2:]
    if not normalized:
        raise ValueError("El UID RFID/NFC no puede estar vacío")
    if any(character not in "0123456789ABCDEF" for character in normalized):
        raise ValueError("El UID RFID/NFC debe contener solo caracteres hexadecimales")
    return normalized
