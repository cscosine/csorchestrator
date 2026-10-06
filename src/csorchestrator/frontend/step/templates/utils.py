import re


def fix_path_repr(src: str) -> str:
    return src.replace("PosixPath(", "Path(").replace("WindowsPath(", "Path(")


def replace_template_variable(
    source: str,
    variable_name: str,
    replacement_value: str,
) -> str:
    pattern = re.compile(
        rf"^(?P<indent>[ \t]*){re.escape(variable_name)}\s*=.*$",
        re.MULTILINE,
    )

    match = pattern.search(source)
    if match is None:
        # TODO add mechanism for not found values
        return source

    indent = match.group("indent")

    replacement_value = variable_name + " = " + replacement_value
    replacement = "\n".join(indent + line if line else line for line in replacement_value.splitlines())

    return source[: match.start()] + replacement + source[match.end() :]


def relocate_portable_imports(code: str) -> str:
    """Rewrite portable imports from csorchestrator to csorchestratorsdk."""
    return code.replace(
        "from csorchestrator.portable",
        "from csorchestratorsdk.portable",
    )
