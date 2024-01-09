import logging
import re
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass

from changelist._objects import ChangeNote, Contributor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MdFormatter:
    """Format release notes in Markdown from PRs, authors and reviewers."""

    repo_name: str
    change_notes: set[ChangeNote]
    authors: set[Contributor]
    reviewers: set[Contributor]

    version: str
    title_template: str
    intro_template: str
    outro_template: str

    # Associate regexes matching PR labels to a section titles in the release notes
    label_section_map: dict[str, str]

    ignored_user_logins: tuple[str, ...]

    def __str__(self) -> str:
        """Return complete release notes document as a string."""
        return self.document

    def __iter__(self) -> Iterable[str]:
        """Iterate the release notes document line-wise."""
        return self.iter_lines()

    @property
    def document(self) -> str:
        """Return complete release notes document as a string."""
        return "".join(self.iter_lines())

    def iter_lines(self) -> Iterable[str]:
        """Iterate the release notes document line-wise."""
        title = self.title_template.format(
            repo_name=self.repo_name, version=self.version
        )
        yield from self._format_section_title(title, level=1)
        yield "\n"
        yield from self._format_intro()
        for title, notes in self._notes_by_section.items():
            yield from self._format_change_section(title, notes)
        yield from self._format_contributor_section(self.authors, self.reviewers)
        yield from self._format_outro()

    @property
    def _notes_by_section(self) -> OrderedDict[str, set[ChangeNote]]:
        """Map change notes to section titles."""
        label_section_map = {
            re.compile(pattern, flags=re.IGNORECASE): section_name
            for pattern, section_name in self.label_section_map.items()
        }

        notes_by_section = OrderedDict()
        for _, section_name in self.label_section_map.items():
            notes_by_section[section_name] = set()
        notes_by_section["Other"] = set()

        for note in self.change_notes:
            matching_sections = [
                section_name
                for regex, section_name in label_section_map.items()
                if any(regex.match(label) for label in note.labels)
            ]
            for section_name in matching_sections:
                notes_by_section[section_name].add(note)
            if not matching_sections:
                logger.warning(
                    "%s without matching label, sorting into section 'Other'",
                    note.reference_url,
                )
                notes_by_section["Other"].add(note)
        return notes_by_section

    def _sanitize_text(self, text: str) -> str:
        """Remove newlines and strip whitespace."""
        text = text.strip()
        text = text.replace("\r\n", " ")
        text = text.replace("\n", " ")
        return text

    def _format_link(self, name: str, target: str) -> str:
        return f"[{name}]({target})"

    def _format_section_title(self, title: str, *, level: int) -> Iterable[str]:
        yield f"{'#' * level} {title}\n"

    def _format_change_note(self, note: ChangeNote) -> Iterable[str]:
        """Format a note about an atomic change."""
        link = self._format_link(note.reference_name, note.reference_url)
        summary = self._sanitize_text(note.content).rstrip(".")
        summary = f"- {summary} ({link}).\n"
        yield summary

    def _format_change_section(
        self, title: str, notes: set[ChangeNote]
    ) -> Iterable[str]:
        """Format a section title and list its items sorted by merge date."""
        if notes:
            yield from self._format_section_title(title, level=2)
            yield "\n"

            for item in sorted(notes, key=lambda note: note.timestamp):
                yield from self._format_change_note(item)
            yield "\n"

    def _format_contributor_line(self, contributor: Contributor) -> str:
        line = contributor.reference_name
        line = self._format_link(line, contributor.reference_url)
        if contributor.name:
            line = f"{contributor.name} ({line})"
        return f"- {line}\n"

    def _format_contributor_section(
        self,
        authors: set[Contributor],
        reviewers: set[Contributor],
    ) -> Iterable[str]:
        """Format contributor section and list users sorted by login handle."""
        authors = {c for c in authors if c.login not in self.ignored_user_logins}
        reviewers = {c for c in reviewers if c.login not in self.ignored_user_logins}

        yield from self._format_section_title("Contributors", level=2)
        yield "\n"

        yield f"{len(authors)} authors added to this release (alphabetically):\n"
        yield "\n"
        author_lines = map(self._format_contributor_line, authors)
        yield from sorted(author_lines, key=lambda s: s.lower())
        yield "\n"

        yield f"{len(reviewers)} reviewers added to this release (alphabetically):\n"
        yield "\n"
        reviewers_lines = map(self._format_contributor_line, reviewers)
        yield from sorted(reviewers_lines, key=lambda s: s.lower())
        yield "\n"

    def _format_intro(self):
        intro = self.intro_template.format(
            repo_name=self.repo_name, version=self.version
        )
        # Make sure to return exactly one line at a time
        yield from (f"{self._sanitize_text(line)}\n" for line in intro.split("\n"))

    def _format_outro(self) -> Iterable[str]:
        outro = self.outro_template.format(
            repo_name=self.repo_name, version=self.version
        )
        # Make sure to return exactly one line at a time
        yield from (f"{self._sanitize_text(line)}\n" for line in outro.split("\n"))


class RstFormatter(MdFormatter):
    """Format release notes in reStructuredText from PRs, authors and reviewers."""

    def _sanitize_text(self, text) -> str:
        """Remove newlines, strip whitespace and convert literals to rST syntax."""
        text = super()._sanitize_text(text)
        text = text.replace("`", "``")
        return text

    def _format_link(self, name: str, target: str) -> str:
        return f"`{name} <{target}>`_"

    def _format_section_title(self, title: str, *, level: int) -> Iterable[str]:
        yield title + "\n"
        underline = {1: "=", 2: "-", 3: "~"}
        yield underline[level] * len(title) + "\n"
