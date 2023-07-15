import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable

import requests_cache
from github import Github
from tqdm import tqdm

from ._format import MdFormatter, RstFormatter
from ._query import commits_between, contributors, pull_requests_from_commits

logger = logging.getLogger(__name__)

here = Path(__file__).parent

REQUESTS_CACHE_PATH = Path(tempfile.gettempdir()) / "github_cache.sqlite"

GH_URL = "https://github.com"


def lazy_tqdm(*args, **kwargs):
    """Defer initialization of progress bar until first item is requested.

    Calling `tqdm(...)` prints the progress bar right there and then. This can scramble
    output, if more than one progress bar are initialized at the same time but their
    iteration is meant to be done later in successive order.
    """
    kwargs["file"] = kwargs.get("file", sys.stderr)
    yield from tqdm(*args, **kwargs)


def parse_command_line(func: Callable) -> Callable:
    """Define and parse command line options.

    Has no effect if any keyword argument is passed to the underlying function.
    """
    parser = argparse.ArgumentParser(
        usage="Prepare an automatic changelog from GitHub's pull requests."
    )
    parser.add_argument(
        "org_repo",
        help="Org and repo name of a repository on GitHub (delimited by a slash), "
        "e.g. 'numpy/numpy'",
    )
    parser.add_argument(
        "start_rev",
        help="The starting revision (excluded), e.g. the tag of the previous release",
    )
    parser.add_argument(
        "stop_rev",
        help="The stop revision (included), e.g. the 'main' branch or the current "
        "release",
    )
    parser.add_argument(
        "--version",
        default="0.0.0",
        help="Version you're about to release, used title and description of the notes",
    )
    parser.add_argument("--out", help="Write to file, prints to STDOUT otherwise")
    parser.add_argument(
        "--format",
        choices=["rst", "md"],
        default="md",
        help="Choose format, defaults to Markdown",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cached requests to GitHub's API before running",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging level",
    )

    def wrapped(**kwargs):
        if not kwargs:
            kwargs = vars(parser.parse_args())
        return func(**kwargs)

    return wrapped


@parse_command_line
def main(
    *,
    org_repo: str,
    start_rev: str,
    stop_rev: str,
    version: str,
    out: str,
    format: str,
    clear_cache: bool,
    verbose: int,
):
    """Main function of the script.

    See :func:`parse_command_line` for a description of the accepted input.
    """
    level = {0: logging.WARNING, 1: logging.INFO}.get(verbose, logging.DEBUG)
    logger.setLevel(level)

    requests_cache.install_cache(
        REQUESTS_CACHE_PATH, backend="sqlite", expire_after=3600
    )
    print(f"Using requests cache at {REQUESTS_CACHE_PATH}", file=sys.stderr)
    if clear_cache:
        requests_cache.clear()
        logger.info("cleared requests cache at %s", REQUESTS_CACHE_PATH)

    gh_token = os.environ.get("GH_TOKEN")
    if gh_token is None:
        raise RuntimeError(
            "You need to set the environment variable `GH_TOKEN`. "
            "The token is used to avoid rate limiting, "
            "and can be created at https://github.com/settings/tokens.\n\n"
            "The token does not require any permissions (we only use the public API)."
        )
    gh = Github(gh_token)

    print("Fetching commits...", file=sys.stderr)
    commits = commits_between(gh, org_repo, start_rev, stop_rev)
    pull_requests = pull_requests_from_commits(
        lazy_tqdm(commits, desc="Fetching pull requests")
    )
    authors, reviewers = contributors(
        gh=gh,
        org_repo=org_repo,
        commits=lazy_tqdm(commits, desc="Fetching authors"),
        pull_requests=lazy_tqdm(pull_requests, desc="Fetching reviewers"),
    )

    Formatter = {"md": MdFormatter, "rst": RstFormatter}[format]
    formatter = Formatter(
        repo_name=org_repo.split("/")[-1],
        pull_requests=pull_requests,
        authors=authors,
        reviewers=reviewers,
        version=version,
    )

    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as io:
            io.writelines(formatter.iter_lines())
    else:
        print()
        for line in formatter.iter_lines():
            assert line.endswith("\n")
            assert line.count("\n") == 1
            print(line, end="", file=sys.stdout)
