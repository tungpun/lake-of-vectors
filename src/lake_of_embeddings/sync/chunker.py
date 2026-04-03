def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4


def chunk_text(
    text: str, max_tokens: int = 500, overlap_tokens: int = 50
) -> list[str]:
    if not text or not text.strip():
        return []

    max_chars = max_tokens * 4
    overlap_chars = overlap_tokens * 4

    # If the whole text fits, return it as a single chunk
    if _estimate_tokens(text) <= max_tokens:
        return [text]

    # Try splitting by separators in order of preference
    separators = ["\n\n", "\n", ". ", " "]
    return _recursive_split(text, separators, max_chars, overlap_chars)


def _recursive_split(
    text: str, separators: list[str], max_chars: int, overlap_chars: int
) -> list[str]:
    if not text.strip():
        return []

    if len(text) <= max_chars:
        return [text]

    # Find the best separator that produces splits
    sep = separators[0] if separators else " "
    remaining_seps = separators[1:] if len(separators) > 1 else separators

    parts = text.split(sep)
    if len(parts) == 1:
        # This separator doesn't help, try the next one
        if remaining_seps and remaining_seps != separators:
            return _recursive_split(text, remaining_seps, max_chars, overlap_chars)
        # Last resort: hard split by character
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunks.append(text[start:end])
            start = end - overlap_chars if end < len(text) else end
        return chunks

    # Merge parts into chunks that fit within max_chars
    chunks = []
    current_parts: list[str] = []
    current_len = 0

    for part in parts:
        part_len = len(part) + (len(sep) if current_parts else 0)

        if current_len + part_len > max_chars and current_parts:
            chunk_text_str = sep.join(current_parts)
            chunks.append(chunk_text_str)

            # Calculate overlap: keep trailing parts that fit in overlap_chars
            overlap_parts: list[str] = []
            overlap_len = 0
            for p in reversed(current_parts):
                if overlap_len + len(p) + len(sep) > overlap_chars:
                    break
                overlap_parts.insert(0, p)
                overlap_len += len(p) + len(sep)

            current_parts = overlap_parts
            current_len = sum(len(p) for p in current_parts) + len(sep) * max(
                0, len(current_parts) - 1
            )

        current_parts.append(part)
        current_len += part_len

    if current_parts:
        final = sep.join(current_parts)
        if final.strip():
            chunks.append(final)

    # Recursively split any chunk that's still too large
    result = []
    for chunk in chunks:
        if len(chunk) > max_chars:
            result.extend(
                _recursive_split(chunk, remaining_seps, max_chars, overlap_chars)
            )
        else:
            result.append(chunk)

    return result
