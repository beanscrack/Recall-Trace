# Contributing to RecallTrace

This is a three-person hackathon project. Read [CLAUDE.md](CLAUDE.md) and the [build brief](docs/BRIEF.md) before changing behavior.

- Fetch the latest `main` before starting and keep work on a feature branch.
- Keep commits focused; coordinate changes to shared API fields and teammate-owned files.
- Preserve recorded decision inputs and tenant boundaries. Replay must never retrieve fresh memories or execute tools.
- Keep credentials in the ignored root `.env`. Use synthetic incident data in examples.
- Run the focused checks for your change. Label mocked checks separately from live Atlas and LLM validation.
- For a pull request, state the behavior changed, validation performed, and remaining demo gaps.

The product name is **RecallTrace**. **Black Box** names its replay feature. The internal `memory_court` database namespace is retained for compatibility and is not a public-facing brand.
