import logging
import re
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Union

from github.NamedUser import NamedUser
from github.PullRequest import PullRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class MdFormatter:
    """Format release notes in Markdown from PRs, authors and reviewers."""

    repo_name: str
    pull_requests: set[PullRequest]
    authors: set[Union[NamedUser]]
    reviewers: set[NamedUser]

    version: str = "x.y.z"
    title_template: str = "{repo_name} {version}"
    intro_template: str = """
We're happy to announce the release of {repo_name} {version}!
"""
    outro_template: str = (
        "_These lists are automatically generated, and may not be complete or may "
        "contain duplicates._\n"
    )
    # Associate regexes matching PR labels to a section titles in the release notes
    regex_section_map: tuple[tuple[str, str], ...] = (
        (".*Highlight.*", "Highlights"),
        (".*New feature.*", "New Features"),
        (".*Enhancement.*", "Enhancements"),
        (".*Performance.*", "Performance"),
        (".*Bug fix.*", "Bug Fixes"),
        (".*API.*", "API Changes"),
        (".*Maintenance.*", "Maintenance"),
        (".*Documentation.*", "Documentation"),
        (".*Infrastructure.*", "Infrastructure"),
    )
    ignored_user_logins: tuple[str] = ("web-flow",)
    pr_summary_regex = re.compile(
        r"^```release-note\s*(?P<summary>[\s\S]*?\w[\s\S]*?)\s*^```", flags=re.MULTILINE
    )

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
        yield from self._format_intro()
        for title, pull_requests in self._prs_by_section.items():
            yield from self._format_pr_section(title, pull_requests)
        yield from self._format_contributor_section(self.authors, self.reviewers)
        yield from self._format_outro()

    @property
    def _prs_by_section(self) -> OrderedDict[str, set[PullRequest]]:
        """Map pull requests to section titles.

        Pull requests whose labels do not match one of the sections given in
        `regex_section_map`, are sorted into a section named "Other".
        """
        label_section_map = {
            re.compile(pattern): section_name
            for pattern, section_name in self.regex_section_map
        }
        prs_by_section = OrderedDict()
        for _, section_name in self.regex_section_map:
            prs_by_section[section_name] = set()
        prs_by_section["Other"] = set()

        for pr in self.pull_requests:
            matching_sections = [
                section_name
                for regex, section_name in label_section_map.items()
                if any(regex.match(label.name) for label in pr.labels)
            ]
            for section_name in matching_sections:
                prs_by_section[section_name].add(pr)
            if not matching_sections:
                logger.warning(
                    "%s without matching label, sorting into section 'Other'",
                    pr.html_url,
                )
                prs_by_section["Other"].add(pr)

        return prs_by_section

    def _sanitize_text(self, text: str) -> str:
        text = text.strip()
        text = text.replace("\r\n", " ")
        text = text.replace("\n", " ")
        return text

    def _format_link(self, name: str, target: str) -> str:
        return f"[{name}]({target})"

    def _format_section_title(self, title: str, *, level: int) -> Iterable[str]:
        yield f"{'#' * level} {title}\n"

    def _parse_pull_request_summary(self, pr: PullRequest) -> str:
        if pr.body and (match := self.pr_summary_regex.search(pr.body)):
            summary = match["summary"]
        else:
            logger.debug("falling back to title for %s", pr.html_url)
            summary = pr.title
        summary = self._sanitize_text(summary)
        return summary

    def _format_pull_request(self, pr: PullRequest) -> Iterable[str]:
        link = self._format_link(f"#{pr.number}", f"{pr.html_url}")
        summary = self._parse_pull_request_summary(pr).rstrip(".")
        summary = f"- {summary} ({link}).\n"
        yield summary

    def _format_pr_section(
        self, title: str, pull_requests: set[PullRequest]
    ) -> Iterable[str]:
        """Format a section title and list its pull requests sorted by merge date."""
        if pull_requests:
            yield from self._format_section_title(title, level=2)
            for pr in sorted(pull_requests, key=lambda pr: pr.merged_at):
                yield from self._format_pull_request(pr)
            yield "\n"

    def _format_user_line(self, user: Union[NamedUser]) -> str:
        line = f"@{user.login}"
        line = self._format_link(line, user.html_url)
        if user.name:
            line = f"{user.name} ({line})"
        return f"- {line}\n"

    def _format_contributor_section(
        self,
        authors: set[Union[NamedUser]],
        reviewers: set[NamedUser],
    ) -> Iterable[str]:
        """Format contributor section and list users sorted by login handle."""
        authors = {u for u in authors if u.login not in self.ignored_user_logins}
        reviewers = {u for u in reviewers if u.login not in self.ignored_user_logins}

        yield from self._format_section_title("Contributors", level=2)
        yield "\n"

        yield f"{len(authors)} authors added to this release (alphabetically):\n"
        author_lines = map(self._format_user_line, authors)
        yield from sorted(author_lines, key=lambda s: s.lower())
        yield "\n"

        yield f"{len(reviewers)} reviewers added to this release (alphabetically):\n"
        reviewers_lines = map(self._format_user_line, reviewers)
        yield from sorted(reviewers_lines, key=lambda s: s.lower())
        yield "\n"

    def _format_intro(self):
        intro = self.intro_template.format(
            repo_name=self.repo_name, version=self.version
        )
        # Make sure to return exactly one line at a time
        yield from (f"{line}\n" for line in intro.split("\n"))

    def _format_outro(self) -> Iterable[str]:
        outro = self.outro_template
        # Make sure to return exactly one line at a time
        yield from (f"{line}\n" for line in outro.split("\n"))


class RstFormatter(MdFormatter):
    """Format release notes in reStructuredText from PRs, authors and reviewers."""

    def _sanitize_text(self, text) -> str:
        text = super()._sanitize_text(text)
        text = text.replace("`", "``")
        return text

    def _format_link(self, name: str, target: str) -> str:
        return f"`{name} <{target}>`_"

    def _format_section_title(self, title: str, *, level: int) -> Iterable[str]:
        yield title + "\n"
        underline = {1: "=", 2: "-", 3: "~"}
        yield underline[level] * len(title) + "\n"
