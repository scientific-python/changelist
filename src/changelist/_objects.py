import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Union

from github.NamedUser import NamedUser
from github.PullRequest import PullRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChangeNote:
    """Describes an atomic change in the notes."""

    content: str
    reference_name: str
    reference_url: str
    labels: tuple[str, ...]
    timestamp: datetime

    @classmethod
    def from_pull_requests(
        cls,
        pull_requests: set[PullRequest],
        *,
        pr_summary_regex: str,
        pr_summary_label_regex: str,
    ) -> "set[ChangeNote]":
        """Create a set of notes from pull requests.

        Create one or more notes describing an atomic change from each given
        pull request.

        `pr_summary_regex` and `pr_summary_label_regex` are used to detect one
        or multiple notes in a pull request description that will be used
        instead of the pull request title if present. This uncouples pull
        requests and notes somewhat. While ideally, a pull request introduces
        a change that would be described in a single note, this is often not
        the case.
        """
        pr_summary_regex = re.compile(pr_summary_regex, flags=re.MULTILINE)
        pr_summary_label_regex = re.compile(pr_summary_label_regex)

        notes = set()
        for pr in pull_requests:
            pr_labels = tuple(label.name for label in pr.labels)

            if not pr.body or not (
                matches := tuple(pr_summary_regex.finditer(pr.body))
            ):
                logger.debug("falling back to title for %s", pr.html_url)
                note = cls(
                    content=pr.title.strip(),
                    reference_name=f"#{pr.number}",
                    reference_url=pr.html_url,
                    labels=pr_labels,
                    timestamp=pr.merged_at,
                )
                notes.add(note)
                continue

            assert len(matches) >= 1
            for match in matches:
                summary = match["summary"]
                label_match = pr_summary_label_regex.search(summary)
                if label_match:
                    labels = tuple(
                        label.strip() for label in label_match["label"].split(",")
                    )
                    # Remove label block
                    summary = pr_summary_label_regex.sub("", summary)
                else:
                    logger.debug(
                        "falling back to PR labels for summary '%r' in %s",
                        summary,
                        pr.html_url,
                    )
                    labels = pr_labels
                note = cls(
                    content=summary.strip(),
                    reference_name=f"#{pr.number}",
                    reference_url=pr.html_url,
                    labels=labels,
                    timestamp=pr.merged_at,
                )
                notes.add(note)
        return notes


@dataclass(frozen=True)
class Contributor:
    """A person mentioned in the notes as an author or reviewer.

    `login` should be the GitHub handle without "@". The "@" is added by the
    `reference_name` property. `reference_url` is typically a URL to the
     contributor's GitHub profile.
    """

    name: Union[str, None]
    login: str
    reference_url: str

    @property
    def reference_name(self) -> str:
        """The GitHub login handle with prefixed "@"."""
        return f"@{self.login}"

    @classmethod
    def from_named_users(cls, named_users: set[NamedUser]) -> "set[Contributor]":
        """ """
        contributors = set()
        for user in named_users:
            contributors.add(
                cls(
                    name=user.name,
                    login=user.login,
                    reference_url=user.html_url,
                )
            )
        return contributors
