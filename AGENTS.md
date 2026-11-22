# AGENTS.md

<!-- cs-template:begin (this block is owned by cs-project-template: do not edit; the rest of the file is the project's) -->
Entry point for coding agents (and people) working in csorchestrator. The rules of every cscosine repository are
in [.claude/cscosine-rules.md](.claude/cscosine-rules.md): read them first. What is specific to this repository
follows this block.

Commands:

- Setup: `./setup.sh` (Windows: `.\setup.ps1`), then `source .venv/bin/activate` (the pre-commit hooks run in it).
- Checks: `pre-commit run --all-files`; tests: `pytest` (`--run-all`: every test, as CI).

Who owns which file (template: [cs-project-template](https://github.com/cscosine/cs-project-template); change it
there, then `copier update --defaults`; never edit its parts here):

- Template: `setup.sh`, `setup.ps1`, `open-code.sh`, `open-code.ps1`, `conftest.py`, `.clang-format`,
  `.vscode/`, `.github/` (the workflows: `checks.yml`, `ci.yml` only), `CLAUDE.md`, `.claude/cscosine-rules.md`, `.claude/settings.json`,
  `LICENSE`.
- Template and project: `pyproject.toml` (template tables between the `template` markers), `.pre-commit-config.yaml` (project hooks
  between the `project: begin` / `project: end` markers), `.gitignore`, `.gitattributes` (project lines after
  `--- project ---`), `README.md` and this file (the
  `cs-template` block).
- The project: everything else.
<!-- cs-template:end -->

## csorchestrator

One Python script per project: run locally or as a generated CI, releases as binary packages

- **Developing csorchestrator**: [.claude/skills/csorchestrator-development/SKILL.md](.claude/skills/csorchestrator-development/SKILL.md).
- **The skill for the projects using csorchestrator**: [agent-plugin/skills/csorchestrator-usage/SKILL.md](agent-plugin/skills/csorchestrator-usage/SKILL.md),
  the Claude Code plugin `csorchestrator` of the `cscosine` marketplace (`cscosine/.github`). A change of the recipe
  API, the CLI or the generated files updates it in the same PR; its `version` in
  `agent-plugin/.claude-plugin/plugin.json` follows the csorchestrator version. Test it with
  `claude --plugin-dir agent-plugin`.
