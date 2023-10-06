"""Update README.md, used by pre-commit."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def get_section_info(file):
    p = Path(file)
    name = p.parts[-1]
    ext = p.suffix[1:]
    begin = rf"<!--- begin {name} --->\n"
    end = rf"<!--- end {name} --->\n"

    with open(PROJECT_ROOT / file) as fh:
        section = fh.read()
        
    section = (
        begin + rf"\n````{ext}\n" + section + r"````\n\n" + end
    )
    return begin, end, section

def main():
    with open(PROJECT_ROOT / "README.md") as fh:
        readme = fh.read()

    # default_config.toml
    begin, end, section = get_section_info("src/changelist/default_config.toml")
    rx = re.compile(begin + ".*?" + end, re.DOTALL)
    # Regex substitution replaces r"\\" with to r"\", compensate
    section = section.replace(r"\\", r"\\\\")
    readme = rx.sub(section, readme)

    # default_config.toml
    begin, end, section = get_section_info(".github/workflows/label-check.yaml")
    rx = re.compile(begin + ".*?" + end, re.DOTALL)
    readme = rx.sub(section, readme)

    # default_config.toml
    begin, end, section = get_section_info(".github/workflows/milestone-merged-prs.yaml")
    rx = re.compile(begin + ".*?" + end, re.DOTALL)
    readme = rx.sub(section, readme)

    with open(PROJECT_ROOT / "README.md", "w") as fh:
        fh.write(readme)


if __name__ == "__main__":
    main()
