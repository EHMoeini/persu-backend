"""Phone normalization and validation helpers."""

from __future__ import annotations

import re

import phonenumbers
from django.core.validators import RegexValidator

# E.164: optional leading +, first digit 1-9, at most 15 digits total.
E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")

validate_phone_e164 = RegexValidator(
    E164_PATTERN,
    "Enter a valid phone number in E.164 format.",
    code="invalid_phone",
)


class InvalidPhoneNumber(ValueError):
    """Raised when a phone number cannot be normalized to valid E.164."""


def normalize_phone(country_code: str, phone: str) -> str:
    """Return an E.164 phone number."""
    if not isinstance(phone, str) or not phone.strip():
        raise InvalidPhoneNumber("A phone number is required.")

    raw = phone.strip()
    cc = (country_code or "").strip() if isinstance(country_code, str) else ""

    try:
        if raw.startswith("+"):
            parsed = phonenumbers.parse(raw, None)
        elif raw.startswith("00"):
            # 00 international prefix.
            parsed = phonenumbers.parse(f"+{raw[2:]}", None)
        elif cc:
            dial_code = cc[1:] if cc.startswith("+") else cc
            if dial_code.isalpha():
                parsed = phonenumbers.parse(raw, dial_code.upper())
            elif dial_code.isdigit():
                digits = re.sub(r"\D", "", raw).lstrip("0")
                parsed = phonenumbers.parse(f"+{dial_code}{digits}", None)
            else:
                raise InvalidPhoneNumber("Enter a valid country code.")
        else:
            raise InvalidPhoneNumber(
                "A country code or an international phone number is required."
            )
    except phonenumbers.NumberParseException as exc:
        raise InvalidPhoneNumber("Enter a valid phone number.") from exc

    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(
        parsed
    ):
        raise InvalidPhoneNumber("Enter a valid phone number.")

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def mask_phone(phone: str) -> str:
    """Mask all but the last four digits."""
    if not phone:
        return "***"
    return f"***{phone[-4:]}"
