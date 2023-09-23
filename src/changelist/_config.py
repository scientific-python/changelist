import logging

from github import Github, UnknownObjectException

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = r'''
[tool.changelist]
title_template = "{repo_name} {version}"
intro_template = "We're happy to announce the release of {repo_name} {version}!"
outro_template = """
_These lists are automatically generated, and may not be complete or may contain
duplicates._
"""
ignored_user_logins = [
    "web-flow",
]
pr_summary_regex = "^```release-note\\s*(?P<summary>[\\s\\S]*?\\w[\\s\\S]*?)\\s*^```"

[tool.changelist.label_section_map]
".*Highlight.*" = "Highlights"
".*New feature.*" = "New Features"
".*Enhancement.*" = "Enhancements"
".*Performance.*" = "Performance"
".*Bug fix.*" = "Bug Fixes"
".*API.*" = "API Changes"
".*Maintenance.*" = "Maintenance"
".*Documentation.*" = "Documentation"
".*Infrastructure.*" = "Infrastructure"
'''


def try_remote_pyproject_config(gh: Github, org_repo: str, *, rev: str) -> str:
    repo = gh.get_repo(org_repo)
    try:
        file = repo.get_contents("pyproject.toml", ref=rev)
        logger.debug("found pyproject.toml in %s@%s", org_repo, rev)
        content = file.decoded_content.decode()
    except UnknownObjectException:
        content = ""
    return content


def parse_pyproject_config(content: str, default_config: str = DEFAULT_CONFIG) -> dict:
    config = tomllib.loads(content).get("tool", {}).get("changelist", {})
    defaults = tomllib.loads(default_config)["tool"]["changelist"]
    for key, value in defaults.items():
        if key not in config:
            config[key] = value
            logger.debug("using default config value for %s", key)
    return config
