"""English source strings and the bundled Simplified Chinese message catalogue."""

import json
from pathlib import Path


LANGUAGES = ("en", "zh-CN")
CHINESE = Path(__file__).with_name("locales") / "zh-CN.json"


def translator(language):
    messages = json.loads(CHINESE.read_bytes()) if language == "zh-CN" else {}

    def translate(message, **values):
        if message is None:
            return messages.get("Not recorded", "Not recorded")
        text = messages.get(message, message)
        return text.format(**values) if values else text

    return translate
