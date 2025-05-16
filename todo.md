## TODO - GitStage CLI

### Core CLI Logic
- [x] Implement `push` command (records commit and pushes to dev)
- [x] Implement `promote` command (moves to testing or main)
- [x] Implement `review` command (approve or reject)
- [ ] Add branch enforcement (only `dev` can push; only `testing` can review)
- [ ] Add duplicate commit check

### Git Features
- [ ] Add `gitstage start feature/<name>` to track branches
- [ ] Add `gitstage status` to show pending promotions and approvals
- [ ] Add rollback support for rejected changes

### Testing
- [ ] Setup pytest
- [ ] Write unit tests for each command

### UX
- [ ] Improve `rich` output for logs
- [ ] Add `gitstage log` command
