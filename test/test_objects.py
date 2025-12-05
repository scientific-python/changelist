from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Union

from changelist._config import DEFAULT_CONFIG_PATH, local_config
from changelist._objects import ChangeNote

here = Path(__file__).parent


DEFAULT_CONFIG = local_config(DEFAULT_CONFIG_PATH)


@dataclass
class _MockUser:
    """Mocks github.User partially."""

    login: str


@dataclass
class _MockLabel:
    """Mocks github.Label.Label partially."""

    name: str


@dataclass
class _MockPullRequest:
    """Mocks github.PullRequest.PullRequest partially."""

    title: str
    body: Union[str, None]
    labels: list[_MockLabel]
    user: _MockUser = field(default_factory=lambda: _MockUser(login="friendlyDev"))
    number: int = (42,)
    html_url: str = "https://github.com/scientific-python/changelist/pull/53"
    merged_at: datetime = datetime(2024, 1, 1)


class Test_ChangeNote:
    def test_from_pull_requests_multiple(self, caplog):
        caplog.set_level("DEBUG")
        body = """
Some ignored text in the pull request body.

```release-note
Deprecate `ìs_odd`; use `not (x % 2)` instead! {label="API, Highlight"}
```
```release-note
Document how to test for oddness of a number.
```

```release-note {.someClass label="Bug fix" otherAttribute="test"}
Make `is_odd()` work for negative numbers.
```
"""
        pull_request = _MockPullRequest(
            title="The title",
            body=body,
            labels=[_MockLabel("Documentation")],
        )
        notes = ChangeNote.from_pull_requests(
            [pull_request],
            pr_summary_regex=DEFAULT_CONFIG["pr_summary_regex"],
            pr_summary_label_regex=DEFAULT_CONFIG["pr_summary_label_regex"],
        )
        assert len(notes) == 3
        notes = sorted(notes, key=lambda n: n.content)
        assert notes[0].content == "Deprecate `ìs_odd`; use `not (x % 2)` instead!"
        assert notes[0].labels == ("API", "Highlight")

        assert notes[1].content == "Document how to test for oddness of a number."
        assert notes[1].labels == ("Documentation",)

        assert notes[2].content == "Make `is_odd()` work for negative numbers."
        assert notes[2].labels == ("Bug fix",)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "DEBUG"
        assert "falling back to PR labels for summary" in caplog.records[0].msg

    def test_from_pull_requests_ignore_by_username(self, caplog):
        caplog.set_level("DEBUG")
        pull_requests = [
            _MockPullRequest(
                title="PR from user",
                body=None,
                labels=[_MockLabel("Documentation")],
                user=_MockUser("someDev"),
            ),
            _MockPullRequest(
                title="PR from bot",
                body=None,
                labels=[_MockLabel("Documentation")],
                user=_MockUser("bot"),
            ),
        ]
        notes = ChangeNote.from_pull_requests(
            pull_requests,
            pr_summary_regex=DEFAULT_CONFIG["pr_summary_regex"],
            pr_summary_label_regex=DEFAULT_CONFIG["pr_summary_label_regex"],
            ignore_prs_by_username=["bot"],
        )
        assert len(notes) == 1
        notes = list(notes)
        assert notes[0].content == "PR from user"
        assert notes[0].labels == ("Documentation",)

        assert len(caplog.records) == 2
        assert caplog.records[0].levelname == "DEBUG"
        assert "falling back to title" in caplog.records[0].msg

        assert caplog.records[1].levelname == "DEBUG"
        assert "skipping PR %s from ignored user %s" in caplog.records[1].msg

    def test_from_pull_requests_fallback_title(self, caplog):
        caplog.set_level("DEBUG")
        pull_request = _MockPullRequest(
            title='The title {label="ignored in title"}',
            body="Nothing here.",
            labels=[_MockLabel("Documentation")],
        )
        notes = ChangeNote.from_pull_requests(
            [pull_request],
            pr_summary_regex=DEFAULT_CONFIG["pr_summary_regex"],
            pr_summary_label_regex=DEFAULT_CONFIG["pr_summary_label_regex"],
        )
        assert len(notes) == 1
        notes = sorted(notes, key=lambda n: n.content)
        assert notes[0].content == 'The title {label="ignored in title"}'
        assert notes[0].labels == ("Documentation",)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "DEBUG"
        assert "falling back to title" in caplog.records[0].msg
