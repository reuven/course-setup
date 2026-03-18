# Feature: Configurable README source

- [x] Create feature branch `feature/readme-source`
- [x] Write tests for config: `readme_source` field in CourseConfig (optional, defaults to None)
- [x] Implement config changes: add `readme_source` to dataclass and `load_config()`
- [x] Write tests for setup_course: README replaced from local file path
- [x] Write tests for setup_course: README replaced from URL
- [x] Write tests for setup_course: default behavior (bundled README) when no readme_source configured
- [x] Implement setup_course changes: fetch/copy README from configured source
- [x] Update init_config template to include readme_source field with comments
- [x] Write test for init_config: template contains readme_source
- [x] Run black, ruff, mypy, and full test suite
- [ ] Commit and merge
