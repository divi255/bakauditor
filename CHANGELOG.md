# Changelog

## 0.1.1

- Support explicitly passwordless restic repositories via `insecure-no-password`.
- Clear inherited password settings for passwordless checks; reject conflicting options.
- Add coverage for explicit passwordless mode.

## 0.1.0

- Require Python 3.10+, PEP 517 packaging and an importable CLI entry point.
- Load YAML safely and validate configuration; empty check sets exit with error.
- Bound subprocess execution, check return codes and safely quote remote commands.
  Pass configured Borg/restic passwords via environment or SSH stdin, not argv.
- Fail individual checks on command/parse errors and continue other checks;
  avoid printing potentially credential-bearing backend error output.
- Detect outdated and future-dated backups; preserve CLI selectors and exit codes.
- Use Borg archive start time for freshness; optionally use native ZFS creation time.
- Calculate directory logical file sizes portably; fix PB display.
- Add restic snapshot freshness and optional restore-size auditing, with filters,
  native remote repository URLs, password files and optional SSH execution.
- Add unit/integration tests and a Python 3.10/3.12/3.14 CI matrix.
