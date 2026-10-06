# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## [0.1.0](https://github.com/pawamoy/git-ew/releases/tag/0.1.0) - 2026-10-06

<small>[Compare with first commit](https://github.com/pawamoy/git-ew/compare/51f9194bfe7f135376dedc9035f0726fb8960a30...0.1.0)</small>

### Features

- Extract and backfill MIME patch attachments ([7e2b3be](https://github.com/pawamoy/git-ew/commit/7e2b3bec937e6aee36d9b40b4d3ff255f244557e) by Timothée Mazzucotelli).
- Add zsh-workers archive ingestion command ([83db052](https://github.com/pawamoy/git-ew/commit/83db052a98b04517e183ed14542e44d534846009) by Timothée Mazzucotelli).
- Support reply-all and archive sent messages ([b02a0f9](https://github.com/pawamoy/git-ew/commit/b02a0f9697c20227dcdd8c40f86c89fa6fc8c9f1) by Timothée Mazzucotelli).
- Add IMAP account configuration and syncing ([1216023](https://github.com/pawamoy/git-ew/commit/1216023772ef150601dbee534f30539be0660ae2) by Timothée Mazzucotelli).
- Hide quoted previous email under details ([a15500e](https://github.com/pawamoy/git-ew/commit/a15500e251ea4f5753ec654f38dd3c8e6fac05c5) by Timothée Mazzucotelli).
- Sync and ingestion of zsh-workers mailing list ([01bc7e9](https://github.com/pawamoy/git-ew/commit/01bc7e9b36b1df7e9e1e70dc84ee18c6b28b8798) by Timothée Mazzucotelli).
- Initial (vibe-coded) version ([51f9194](https://github.com/pawamoy/git-ew/commit/51f9194bfe7f135376dedc9035f0726fb8960a30) by Timothée Mazzucotelli).

### Bug Fixes

- Resolve type-checking errors ([7f4165a](https://github.com/pawamoy/git-ew/commit/7f4165a9ee817f934beac0b9d8a3becc7aee4453) by Timothée Mazzucotelli).
- Filter archive ingestion by date ([49ce25a](https://github.com/pawamoy/git-ew/commit/49ce25afda1d0389006afce98d42a25cb0df7176) by Timothée Mazzucotelli).
- Allow SMTP without authentication ([0187fa0](https://github.com/pawamoy/git-ew/commit/0187fa006797d6d72586914ddbdfb3e28db03ce8) by Timothée Mazzucotelli).
- Report email synchronization failures ([b861fd6](https://github.com/pawamoy/git-ew/commit/b861fd6a6fe95b58c3228057ad31c674aacbdc8d) by Timothée Mazzucotelli).
- Correct collapsing/expanding behavior ([469af2b](https://github.com/pawamoy/git-ew/commit/469af2b4ad1658e96f67a95c5fda822a7e66c848) by Timothée Mazzucotelli).
- Fix decoding (UTF8) ([821f4a8](https://github.com/pawamoy/git-ew/commit/821f4a82fae36e4582accd2f415ac9d04b217383) by Timothée Mazzucotelli).
- Collapsing/unfolding threads ([783f968](https://github.com/pawamoy/git-ew/commit/783f9685a4b630669e67a148c10d39821935ad21) by Timothée Mazzucotelli).

### Code Refactoring

- Use logging outside the CLI ([8099404](https://github.com/pawamoy/git-ew/commit/809940439d4ed73721d5a2130aa3b9b358ae422f) by Timothée Mazzucotelli).
- Simplify thread views ([1095340](https://github.com/pawamoy/git-ew/commit/1095340d4ec84faffe74fde04286181543ad6f07) by Timothée Mazzucotelli).
- Better indentation (visual indications of branching vs single reply) ([45bdff6](https://github.com/pawamoy/git-ew/commit/45bdff64cff1221a86bdab887f8ea5bba50a071d) by Timothée Mazzucotelli).
