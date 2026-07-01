import re


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r'\s+', ' ', text)

    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)

    text = re.sub(r'[•●○■◆]', '-', text)

    text = text.strip()

    return text


def split_into_chunks(text: str, max_chars: int = 3000) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current = []
    current_len = 0

    for paragraph in text.split('\n'):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if current_len + len(paragraph) + 1 > max_chars and current:
            chunks.append('\n'.join(current))
            current = []
            current_len = 0
        current.append(paragraph)
        current_len += len(paragraph) + 1

    if current:
        chunks.append('\n'.join(current))

    return chunks if chunks else [text]
