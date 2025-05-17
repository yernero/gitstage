## TODO - GitStage CLI

### Core CLI Logic
- [x] Implement `push` command (records commit and pushes to dev)
- [x] Implement `promote` command (moves to testing or main)
- [x] Implement `review` command (approve or reject)
- [x] Implement `init` command (initialize repository with stageflow)
- [x] Implement `branch` command (list and switch branches)
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

### UX
- [x] Improve `rich` output for logs
- [ ] Add `gitstage log` command
- [ ] Add progress indicators for long operations
- [ ] Add more detailed error messages
- [ ] Add command aliases for common operations
- [ ] Add interactive mode for complex operations

### Documentation
- [x] Update README with command documentation
- [ ] Add detailed usage examples
- [ ] Add troubleshooting guide
- [ ] Add contribution guidelines
- [ ] Add architecture documentation
