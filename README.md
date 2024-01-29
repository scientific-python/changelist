# changelist

A tool that automates release note generation.

For example, see
https://github.com/scientific-python/changelist/blob/main/CHANGELOG.md.

**Features**

- Compile a list of pull requests, code authors, and reviewers between
  two given git commits.
- Categorize pull requests into sections based on GitHub labels.
- Override pull request titles with more descriptive summaries.
- Document unrelated changes in a pull requests in separate summaries.

_This project is currently in its alpha stage and might be incomplete or change a lot!_

## Installation

```sh
pip install changelist
```

## Usage

The script requires a [GitHub personal access
token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
The token does not need any permissions, since it is used only to
increase query limits.

```sh
export GH_TOKEN='...'
changelist scientific-python/changelist v0.2.0 main
```

This will list all pull requests, authors and reviewers that touched commits
between `v0.2.0` and `main` (excluding `v0.2.0`).
Pull requests are sorted into sections according to the configuration in
`tool.changelist.label_section_map`.

## Writing pull request summaries

By default, changelist will fall back to the title of a pull request and its
GitHub labels to sort it into the appropriate section. However, if you want
longer summaries of your changes you can add a code block with the following
form anywhere in the description of the pull request:

    ```release-note
    An ideally expressive description of the change that is included as
    a single bullet point. Newlines are removed.
    ```

Sometimes pull requests introduce multiple changes that should be listed in different
sections. For that reason, a summary block like above can be used more than
once. Additionally, you can add independent labels to each summary by adding a
`{label="..."}` anywhere in the summary. These labels are sorted the same way
as regular pull request labels are. E.g. the two summaries below will go into
separate sections:

    ```release-note {label="Bug fix"}
    Make `is_odd()` work for negative numbers.
    ```

    ```release-note
    Deprecate `ìs_odd`; use `not (x % 2)` instead! {label="API, Highlight"}
    ```

## Configuration

changelist can be configured from two sources, in order of precedence:

- A local TOML file specified with the `--config` option
- A remote `pyproject.toml` at `stop_rev`

If a configuration option is not specified in either file above, changelist
falls back to the following configuration:

<!--- Changes to the following block are overridden by a pre-commit hook! --->
<!--- begin default_config.toml --->

````toml
# Default changelist configuration as supported in pyproject.toml
[tool.changelist]

# A template string that is included as the title of the generated notes.
# "{repo_name}" and "{version}", if given, are replaced by the respective
# values given in the command line.
title_template = "{repo_name} {version}"

# A template string that is included as introductory text after the title.
# "{repo_name}" and "{version}", if given, are replaced by the respective
# values given in the command line.
intro_template = """
We're happy to announce the release of {repo_name} {version}!
"""

# A template string that is included at the end of the generated notes.
# "{repo_name}" and "{version}", if given, are replaced by the respective
# values given in the command line.
outro_template = """
_These lists are automatically generated, and may not be complete or may contain
duplicates._
"""

# Profiles that are excluded from the contributor list.
ignored_user_logins = [
    "web-flow",
]

# If this regex matches a pull requests description, the captured content
# is included instead of the pull request title. E.g. the
# default regex below is matched by
#
# ```release-note
# An ideally expressive description of the change that is included as
# a single bullet point. Newlines are removed.
# ```
#
# If you modify this regex, make sure to match the content with a capture
# group named "summary". The regex is allowed to match more than once in which
# case a single pull request may result in multiple items (see
# `pr_summary_label_regex` for why that might be useful).
pr_summary_regex = "^```release-note\\s*(?P<summary>[\\s\\S]*?\\w[\\s\\S]*?)\\s*^```"

# Sometimes pull requests introduce changes that should be listed in different
# sections. For that reason, `pr_summary_regex` can match more than once and
# this regex, `pr_summary_label_regex`, can be used to add independent labels
# to each summary. These labels are sorted with the `label_section_map` the
# same way as regular pull request labels are. E.g. the example below will both
# match and go into separate sections:
#
# ```release-note {label="Bug fix"}
# Make `is_odd()` work for negative numbers.
# ```
#
# ```release-note
# Deprecate `ìs_odd`; use `not (x % 2)` instead! {label="API, Highlight"}
# ```
#
# If you modify this regex, make sure to match the content with a capture
# group named "label".
pr_summary_label_regex = """{[^}]*?label=[\\"](?P<label>[^\\"]+)[^}]*?}"""

# If any of a pull request's labels matches one of the regexes on the left side
# its summary will appear in the appropriate section with the title given on
# the right side. If a pull request doesn't match one of these categories it is
# sorted into a section titled "Other". Pull request can appear in multiple
# sections as long as their labels match.
[tool.changelist.label_section_map]
".*Highlight.*" = "Highlights"
".*New feature.*" = "New Features"
".*API.*" = "API Changes"
".*Enhancement.*" = "Enhancements"
".*Performance.*" = "Performance"
".*Bug fix.*" = "Bug Fixes"
".*Documentation.*" = "Documentation"
".*Infrastructure.*" = "Infrastructure"
".*Maintenance.*" = "Maintenance"
````

<!--- end default_config.toml --->

## Set up your repository

To categorize merged PRs in the changelist with the default configuration, each
PR must have a label that matches one of the regexes on the left side of the
`label_section_map` table, e.g. `type: Highlights`.

### Label checking

You may want to ensure that each PR has an associated `type: ` label,
we recommend adding an action that fails CI if the label is missing.

To do so, place the following in `.github/workflows/label-check.yaml`:

<!--- Changes to the following block are overridden by a pre-commit hook! --->
<!--- begin label-check.yaml --->

```yaml
name: Labels

on:
  pull_request:
    types:
      - opened
      - reopened
      - labeled
      - unlabeled
      - synchronize

env:
  LABELS: ${{ join( github.event.pull_request.labels.*.name, ' ' ) }}

jobs:
  check-type-label:
    name: ensure type label
    runs-on: ubuntu-latest
    steps:
      - if: "contains( env.LABELS, 'type: ' ) == false"
        run: exit 1
```

<!--- end label-check.yaml --->

### Milestones

Often, it is helpful to have milestones that reflect the actual PRs
merged. We therefore recommend adding an action that attached the
next open milestone to any merged PR.

To do so, place the following in `.github/workflows/milestone-merged-prs.yaml`:

<!--- Changes to the following block are overridden by a pre-commit hook! --->
<!--- begin milestone-merged-prs.yaml --->

```yaml
name: Milestone

on:
  pull_request_target:
    types:
      - closed
    branches:
      - "main"

jobs:
  milestone_pr:
    name: attach to PR
    runs-on: ubuntu-latest
    steps:
      - uses: scientific-python/attach-next-milestone-action@bc07be829f693829263e57d5e8489f4e57d3d420
        with:
          token: ${{ secrets.MILESTONE_LABELER_TOKEN }}
          force: true
```

<!--- end milestone-merged-prs.yaml --->

See https://github.com/scientific-python/attach-next-milestone-action for more information.
