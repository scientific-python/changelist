# changelist

Prepare an automatic changelog from GitHub pull requests

_This project is currently in its alpha stage and might be incomplete or change a lot!_

## Installation

```sh
pip install changelist
```

## Set up your repository

All PRs must have one of the following labels:

- `type: Highlights`
- `type: New features`
- `type: Enhancements`
- `type: Performance`
- `type: Bug fix`
- `type: API`
- `type: Maintenance`
- `type: Documentation`
- `type: Infrastructure`

### Label checking

To ensure that each PR has one of the above labels attached to it,
we recommend adding the following to `.github/workflows/label-check.yaml`:

```
name: Labels

on:
  pull_request:
    types:
      - opened
      - labeled
      - unlabeled

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

We also recommend adding `.github/workflows/milestone-merged-prs.yaml`:

```
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
      - uses: scientific-python/attach-next-milestone-action@f94a5235518d4d34911c41e19d780b8e79d42238
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
