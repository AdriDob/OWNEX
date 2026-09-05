Requesting review for: chore(release): add preliminary FINAL_RELEASE_REPORT and artifacts

PR: https://github.com/AdriDob/OWNEX/pull/37

Suggested reviewers:
- @AdriDob (owner)
- QA team: please review the FINAL_RELEASE_REPORT.md, `docs/tauri_windows_validation.md` and the artifacts under `artifacts/release/`.

Checklist for reviewers:
- Verify `FINAL_RELEASE_REPORT.md` contents and findings.
- Validate test artifacts (`pytest_fast_output.txt`, `make_test_output.txt`).
- Run the Tauri Windows validation checklist on a Windows machine and attach results.
- Confirm no urgent blockers before promoting to RC.

Notes:
- GitHub reported Dependabot alerts on the default branch; address security findings separately.
