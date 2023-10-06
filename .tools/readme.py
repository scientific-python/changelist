"""Update README.md, used by pre-commit."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def main():
    with open(PROJECT_ROOT / "README.md") as fh:
        readme = fh.read()

    with open(PROJECT_ROOT / "src/changelist/default_config.toml") as fh:
        default_config = fh.read()

    config_begin = r"<!--- begin default_config.toml --->\n"
    config_end = r"<!--- end default_config.toml --->\n"
    config_section = (
        config_begin + r"\n````toml\n" + default_config + r"````\n\n" + config_end
    )

    rx = re.compile(config_begin + ".*?" + config_end, re.DOTALL)
    # Regex substitution replaces r"\\" with to r"\", compensate
    config_section = config_section.replace(r"\\", r"\\\\")
    readme = rx.sub(config_section, readme)

    with open(PROJECT_ROOT / "README.md", "w") as fh:
        fh.write(readme)


if __name__ == "__main__":
    main()
