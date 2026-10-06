from yaml import SafeDumper
from yaml.nodes import ScalarNode


class LiteralString(str):
    pass


def literal_string_representer(
    dumper: SafeDumper,
    data: LiteralString,
) -> ScalarNode:
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str",
        str(data),
        style="|",
    )


SafeDumper.add_representer(
    LiteralString,
    literal_string_representer,
)
