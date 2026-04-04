import re
from typing import Optional


JASC_PATTERN = re.compile(r'^(\d{2})-(\d{2})-(\d{2})$')


def normalize_jasc(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip().upper()
    text = text.replace(' ', '').replace('_', '-').replace('/', '-')

    if re.fullmatch(r'\d{6}', text):
        return f'{text[0:2]}-{text[2:4]}-{text[4:6]}'

    match = JASC_PATTERN.match(text)
    if match:
        return text

    return None

