import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass

import requests
from github import Github
from github.Commit import Commit
from github.NamedUser import NamedUser
from github.PullRequest import PullRequest

logger = logging.getLogger(__name__)


def commits_between(
    gh: Github, org_name: str, start_rev: str, stop_rev: str
) -> set[Commit]:
    """Fetch commits between two revisions excluding the commit of `start_rev`."""
    repo = gh.get_repo(org_name)
    comparison = repo.compare(base=start_rev, head=stop_rev)
    commits = set(comparison.commits)
    assert repo.get_commit(start_rev) not in commits
    assert repo.get_commit(stop_rev) in commits
    return commits


def pull_requests_from_commits(commits: Iterable[Commit]) -> set[PullRequest]:
    """Fetch pull requests that are associated with the given `commits`."""
    all_pull_requests = set()
    for commit in commits:
        commit_pull_requests = list(commit.get_pulls())
        if len(commit_pull_requests) != 1:
            logger.info(
                "%s with no or multiple PR(s): %r",
                commit.html_url,
                [p.html_url for p in commit_pull_requests],
            )
        if any(not p.merged for p in commit_pull_requests):
            logger.error(
                "%s with unmerged PRs: %r",
            )
        for pull in commit_pull_requests:
            if pull in all_pull_requests:
                # Expected if pull request is merged without squashing
                logger.debug(
                    "%r associated with multiple commits",
                    pull.html_url,
                )
        all_pull_requests.update(commit_pull_requests)
    return all_pull_requests


@dataclass(frozen=True, kw_only=True)
class GitHubGraphQl:
    """Interface to query GitHub's GraphQL API for a particular repository."""

    org_name: str
    repo_name: str

    URL: str = "https://api.github.com/graphql"
    GRAPHQL_AUTHORS: str = """
    query {{
      repository (owner: "{org_name}" name: "{repo_name}") {{
        object(expression: "{commit_sha}" ) {{
          ... on Commit {{
            commitUrl
            authors(first:{page_limit}) {{
              edges {{
                cursor
                node {{
                  name
                  email
                  user {{
                    login
                    databaseId
                  }}
                }}
              }}
            }}
          }}
        }}
      }}
    }}
    """
    PAGE_LIMIT: int = 100

    def _run_query(self, query: str) -> dict:
        """Fetch results for a GraphQl query."""
        headers = {"Authorization": f"Bearer {os.environ.get('GH_TOKEN')}"}
        sanitized_query = json.dumps({"query": query.replace("\n", "")})
        response = requests.post(self.URL, data=sanitized_query, headers=headers)
        data = response.json()
        return data

    def find_authors(self, commit_sha: str) -> dict[int, str]:
        """Find ID and login of (co-)author(s) for a commit.

        Other than GitHub's REST API, the GraphQL API supports returning all authors,
        including co-authors, of a commit.
        """
        query = self.GRAPHQL_AUTHORS.format(
            org_name=self.org_name,
            repo_name=self.repo_name,
            commit_sha=commit_sha,
            page_limit=self.PAGE_LIMIT,
        )
        data = self._run_query(query)
        commit = data["data"]["repository"]["object"]
        edges = commit["authors"]["edges"]
        if len(edges) == self.PAGE_LIMIT:
            # TODO implement pagination if this becomes an issue, e.g. see
            # https://github.com/scientific-python/devstats-data/blob/e3cd826518bf590083409318b0a7518f7781084f/query.py#L92-L107
            logger.warning(
                "reached page limit while querying authors in %r, "
                "only the first %i authors will be included",
                commit["commitUrl"],
                self.PAGE_LIMIT,
            )

        coauthors = {}
        for _i, edge in enumerate(edges):
            node = edge["node"]
            user = node["user"]
            if user is None:
                logger.warning(
                    "could not determine GitHub user for %r in %r",
                    node,
                    commit["commitUrl"],
                )
                continue
            coauthors[user["databaseId"]] = user["login"]

        assert coauthors
        return coauthors


def contributors(
    gh: Github,
    org_repo: str,
    commits: Iterable[Commit],
    pull_requests: Iterable[PullRequest],
) -> tuple[set[NamedUser], set[NamedUser]]:
    """Fetch commit authors, co-authors and reviewers.

    `authors` are users which created or co-authored a commit.
    `reviewers` are users, who added reviews to a merged pull request or merged a
    pull request (committer of the merge commit).
    """
    authors = set()
    reviewers = set()

    org_name, repo_name = org_repo.split("/")
    ql = GitHubGraphQl(org_name=org_name, repo_name=repo_name)

    for commit in commits:
        if commit.author:
            authors.add(commit.author)
        if commit.committer:
            reviewers.add(commit.committer)
        if "Co-authored-by:" in commit.commit.message:
            # Fallback on GraphQL API to find co-authors as well
            user_ids = ql.find_authors(commit.sha)
            for user_id, user_login in user_ids.items():
                named_user = gh.get_user_by_id(user_id)
                assert named_user.login == user_login
                authors.add(named_user)
        else:
            logger.debug("no co-authors in %r", commit.html_url)

    for pull in pull_requests:
        for review in pull.get_reviews():
            if review.user:
                reviewers.add(review.user)

    return authors, reviewers
