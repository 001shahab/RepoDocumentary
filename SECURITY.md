# Security policy

## Supported versions

Security fixes are released for the latest minor version.

## Reporting a vulnerability

Please do not open a public issue for security problems. Email
Prof. Shahab Anbarjafari at shb@3sholding.com with a description, steps to
reproduce and the affected version. You will receive an acknowledgement within
five working days.

## Scope notes

- RepoDocumentary reads commit metadata and line counts only. It never reads file contents.
- When the OpenAI narrator is used, commit messages and contributor names are sent to the
  configured endpoint. Use `--offline` or `--anonymize` when that is not acceptable.
- Never commit your `.env` file. It is excluded by the provided `.gitignore`.
