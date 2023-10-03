import re

with open("README.md") as fh:
    readme = fh.read()

with open("src/changelist/default_config.toml") as fh:
    default_config = fh.read()

config_begin = r"<!--- begin default_config.toml --->\n"
config_end = r"<!--- end default_config.toml --->\n"
config_section = (
    config_begin + r"\n````toml\n" + default_config + r"````\n\n" + config_end
)

rx = re.compile(config_begin + ".*?" + config_end, re.DOTALL)
readme = rx.sub(config_section, readme)


with open("README.md", "w") as fh:
    fh.write(readme)
