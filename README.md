# changelist

Prepare an automatic changelog from GitHub pull requests.

_This project is currently in its alpha stage and might be incomplete or change a lot!_

## Installation

```sh
pip install changelist
```

## Set up your repository

To categorize merged PRs in the changelist, each PR
must have have one of the following labels:

- `type: Highlights`
- `type: New features`
- `type: Enhancements`
- `type: Performance`
- `type: Bug fix`
- `type: API`
- `type: Maintenance`
- `type: Documentation`
- `type: Infrastructure`

This list will soon be configurable.

### Label checking

To ensure that each PR has an associated `type: ` label,
we recommend adding an action that fails CI if the label is missing.

To do so, place the following in `.github/workflows/label-check.yaml`:

```yaml
name: Labels

on:
  pull_request:
    types:
      - opened
      - repoened
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

### Milestones

Often, it is helpful to have milestones that reflect the actual PRs
merged. We therefore recommend adding an action that attached the
next open milestone to any merged PR.

To do so, place the following in `.github/workflows/milestone-merged-prs.yaml`:

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

See https://github.com/scientific-python/attach-next-milestone-action for more information.

## Usage

```sh
export GH_TOKEN='...'
changelist scikit-image/scikit-image v0.21.0 main
```

The script requires a [GitHub personal access
token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
The token does not need any permissions, since it is used only to
increase query limits.
