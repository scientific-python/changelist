from datetime import datetime
from pathlib import Path

from changelist._format import ChangeNote, Contributor, MdFormatter, RstFormatter

here = Path(__file__).parent

NOTES = (
    ChangeNote(
        content="Add `foo`.",
        reference_name="#1",
        reference_url="https://github.com/foo-group/foolib/pull/1",
        labels=("New feature",),
        timestamp=datetime(2023, 1, 1),
    ),
    ChangeNote(
        content="Deprecate `bar`",
        reference_name="#1",
        reference_url="https://github.com/foo-group/foolib/pull/1",
        labels=("api", "Bug fix"),
        timestamp=datetime(2023, 1, 1),
    ),
    ChangeNote(
        content="Create tutorial\nabout newlines.",
        reference_name="#2",
        reference_url="https://github.com/foo-group/foolib/pull/2",
        labels=("documentation",),
        timestamp=datetime(2023, 1, 2),
    ),
    ChangeNote(
        content="Unlabeled change. With\nmultiple sentences.",
        reference_name="#2",
        reference_url="https://github.com/foo-group/foolib/pull/3",
        labels=(),
        timestamp=datetime(2023, 1, 3),
    ),
)

CONTRIBUTORS = (
    Contributor(
        name="Nur Lungile",
        login="lungile",
        reference_url="https://github.com/lungile",
    ),
    Contributor(
        name=None,
        login="madhu-esen",
        reference_url="https://github.com/madhu-esen",
    ),
    Contributor(
        name="bot",
        login="bot",
        reference_url="https://github.com/apps/bot",
    ),
)

LABEL_SECTION_MAP = {
    ".*New feature.*": "New Features",
    ".*API.*": "API Changes",
    ".*Bug fix.*": "Bug Fixes",
    ".*Documentation.*": "Documentation",
}

DEFAULT_FORMATTER_KWARGS = {
    "repo_name": "foolib",
    "change_notes": set(NOTES),
    "authors": set(CONTRIBUTORS),
    "reviewers": set(CONTRIBUTORS),
    "version": "1.0",
    "title_template": "{repo_name} {version}",
    "intro_template": "Intro with `literal` for {repo_name} {version}!\n",
    "outro_template": "Outro with `literal`.",
    "label_section_map": LABEL_SECTION_MAP,
    "ignored_user_logins": ("bot"),
}


class Test_MdFormatter:
    def test_iteration(self):
        formatter = MdFormatter(**DEFAULT_FORMATTER_KWARGS)
        for line in formatter:
            assert line.endswith("\n")
            assert line.count("\n") == 1

    def test_full(self):
        formatter = MdFormatter(**DEFAULT_FORMATTER_KWARGS)
        result = str(formatter)
        with (here / "desired_notes.md").open() as file:
            desired = file.read()
        assert result == desired


class Test_RstFormatter:
    def test_iteration(self):
        formatter = RstFormatter(**DEFAULT_FORMATTER_KWARGS)
        for line in formatter:
            assert line.endswith("\n")
            assert line.count("\n") == 1

    def test_full(self):
        formatter = RstFormatter(**DEFAULT_FORMATTER_KWARGS)
        result = str(formatter)
        with (here / "desired_notes.rst").open() as file:
            desired = file.read()
        assert result == desired
