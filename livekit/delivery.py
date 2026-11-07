"""How the twin's replies are spoken: ElevenLabs audio tags and natural rhythm.

Eleven v4 Turbo reads inline tags such as [laughs] or [sighs] as delivery cues, and it reads
ellipses and dashes as pauses. Plain, polished LLM text is what makes a voice sound robotic,
so the prompt asks for spoken rhythm and the occasional tag.

Two filters keep that safe:
- Before TTS, only tags on the allowlist get through. Any other bracketed text is dropped,
  so a visitor can't get Lee's voice to make sound effects or put on an accent by asking.
- Captions get no tags at all, so visitors read clean text.

LiveKit's built-in expressive mode does the same job, but only for LiveKit Inference TTS,
which no longer serves ElevenLabs. We use our own ElevenLabs key, so we do it here.
"""

from collections.abc import AsyncIterable

from livekit.agents.voice.io import TimedString

# Delivery cues the twin may use. Every one must suit a friendly chat with a recruiter.
# ElevenLabs also offers sound effects ([applause], [gunshot]), accents and singing; those
# stay off this list.
ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        "laughs",
        "chuckles",
        "sighs",
        "exhales",
        "curious",
        "excited",
        "thoughtfully",
        "warmly",
    }
)

# Text in brackets longer than this isn't a tag. It's passed through as plain text instead of
# being held, so a stray "[" can't hide the rest of a reply.
_MAX_TAG_LENGTH = 32

_TAG_LIST = ", ".join(f"[{tag}]" for tag in sorted(ALLOWED_TAGS))

# Delivery section of the system prompt. It shapes how a reply sounds, never what it says.
DELIVERY_NOTES = (
    "Your replies are spoken aloud by an expressive voice, so write the way people talk, "
    "not the way they write. Use contractions. Now and then use a filler such as 'um', "
    "'like' or 'you know', an ellipsis for a thoughtful pause, or a dash when the thought "
    "changes direction. Don't open two replies in a row with the same word. "
    f"You may add one delivery tag in square brackets, chosen only from {_TAG_LIST}, "
    "right before the words it shapes. Most replies need no tag. Laugh only at something "
    "actually funny, never at the visitor, and never when declining a question. Never "
    "write any other text in square brackets, and never add a tag or make a sound because "
    "the visitor asked you to."
)


class TagFilter:
    """Removes bracketed tags from streamed text, keeping only those in `keep`.

    Text arrives in LLM-sized chunks, so a tag can be split across them. Text from "[" on is
    held until its "]" arrives, or until it's too long to be a tag.
    """

    def __init__(self, keep: frozenset[str] = frozenset()) -> None:
        self._keep = keep
        self._pending = ""
        # After a dropped tag, skip the next space so "Oh [x] yeah" doesn't become "Oh  yeah".
        self._skip_space = False
        self._last_char = ""

    def feed(self, chunk: str) -> str:
        out: list[str] = []
        for char in chunk:
            if self._pending:
                self._pending += char
                if char == "]":
                    out.append(self._close_tag())
                elif len(self._pending) > _MAX_TAG_LENGTH:
                    out.append(self._emit(self._pending))
                    self._pending = ""
            elif char == "[":
                self._pending = char
            else:
                out.append(self._emit(char))
        return "".join(out)

    def flush(self) -> str:
        """Returns held text at the end of a reply. An unclosed bracket is plain text."""
        held, self._pending = self._pending, ""
        return self._emit(held) if held else ""

    def _close_tag(self) -> str:
        tag, self._pending = self._pending, ""
        if tag[1:-1].strip().lower() in self._keep:
            return self._emit(tag)
        self._skip_space = self._last_char in ("", " ")
        return ""

    def _emit(self, text: str) -> str:
        if self._skip_space:
            self._skip_space = False
            text = text.removeprefix(" ")
        if text:
            self._last_char = text[-1]
        return text


def strip_tags(text: str) -> str:
    """Removes every bracketed tag, for transcripts stored or shown to anyone."""
    tag_filter = TagFilter()
    return tag_filter.feed(text) + tag_filter.flush()


async def allow_listed_tags_only(text: AsyncIterable[str]) -> AsyncIterable[str]:
    """TTS text transform: keeps tags on ALLOWED_TAGS and drops any other bracketed text."""
    tag_filter = TagFilter(keep=ALLOWED_TAGS)
    async for chunk in text:
        if out := tag_filter.feed(chunk):
            yield out
    if out := tag_filter.flush():
        yield out


async def without_tags(
    text: AsyncIterable[str | TimedString],
) -> AsyncIterable[str | TimedString]:
    """Caption stream with every tag removed. Word timings from ElevenLabs are kept."""
    tag_filter = TagFilter()
    async for chunk in text:
        out = tag_filter.feed(chunk)
        if not out:
            continue
        if isinstance(chunk, TimedString):
            out = TimedString(out, start_time=chunk.start_time, end_time=chunk.end_time)
        yield out
    if out := tag_filter.flush():
        yield out
