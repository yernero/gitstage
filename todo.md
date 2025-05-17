## TODO - GitStage CLI

### Core CLI Logic
- [x] Implement `push` command (records commit and pushes to dev)
- [x] Implement `promote` command (moves to testing or main)
- [x] Implement `review` command (approve or reject)
- [x] Implement `init` command (initialize repository with stageflow)
- [x] Implement `branch` command (list and switch branches)
- [x] Add commit hash tracking to push promotion
- [x] Prevent re-promotion of already promoted commits
- [x] Skip promotions if no new file changes
- [x] Add --force-promote flag to override push validation
- [x] Implement flatten cascade top-down
- [x] Improve `flatten` UX and add dry-run, force flags
- [x] Add bulk approval support to review command (--all)
- [ ] Add branch enforcement (only `dev` can push; only `testing` can review)
- [ ] Add duplicate commit check
- [ ] Add branch tracking for feature branches

### Git Features
- [x] Add branch management with `gitstage branch`
- [ ] Add `gitstage start feature/<name>` to track branches
- [ ] Add `gitstage status` to show pending promotions and approvals
- [ ] Add rollback support for rejected changes
- [ ] Add support for branch protection rules
- [ ] Add support for merge conflicts resolution

### Testing
- [ ] Setup pytest
- [ ] Write unit tests for each command
- [ ] Add integration tests for workflow scenarios
- [ ] Add test coverage reporting
- [ ] Add integration tests for `flatten --cascade` and `push` with edge cases

### UX
- [x] Improve `rich` output for logs
- [x] Add progress indicators for long operations
- [x] Add more detailed error messages
- [ ] Add command aliases for common operations
- [ ] Add interactive mode for complex operations

### Documentation
- [x] Update README with command documentation
- [x] Add detailed usage examples
- [ ] Add troubleshooting guide
- [ ] Add contribution guidelines
- [ ] Add architecture documentation
