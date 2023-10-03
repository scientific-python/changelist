import logging
from pathlib import Path

from github import Github, UnknownObjectException

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

logger = logging.getLogger(__name__)

here = Path(__file__)


DEFAULT_CONFIG_PATH = here.parent / "default_config.toml"


def remote_config(gh: Github, org_repo: str, *, rev: str):
    repo = gh.get_repo(org_repo)
    try:
        file = repo.get_contents("pyproject.toml", ref=rev)
        logger.debug("found pyproject.toml in %s@%s", org_repo, rev)
        content = file.decoded_content.decode()
    except UnknownObjectException:
        content = ""
    config = tomllib.loads(content)
    config = config.get("tool", {}).get("changelist", {})
    return config


def local_config(path: Path) -> dict:
    with path.open("rb") as fp:
        config = tomllib.load(fp)
    config = config.get("tool", {}).get("changelist", {})
    return config


def add_config_defaults(
    config: dict, *, default_config_path: Path = DEFAULT_CONFIG_PATH
) -> dict:
    with default_config_path.open("rb") as fp:
        defaults = tomllib.load(fp)
    defaults = defaults["tool"]["changelist"]
    for key, value in defaults.items():
        if key not in config:
            config[key] = value
            logger.debug("using default config value for %s", key)
    return config
