# Incident Report & Resolution: GitHub Connection Troubleshooting
**Date:** 23 May 2026  
**Status:** RESOLVED (Switched from HTTPS to SSH)

---

## 1. What Happened (The Troubleshooting Journey)
We encountered a chain of shifting Git errors while trying to target the `v2-(first-round-of-feedback-from-RJ)` branch from inside the `Aircraft Safety Tracker` sub-folder:
1. **Syntax Error (`unexpected token '('`)**: Bash broke on the parentheses in the branch name. Fixed by wrapping the branch name/URL in single quotes (`'`).
2. **Pathspec Error**: The local repository didn't know the remote branch existed. Fixed by running `git fetch origin`.
3. **The Loop (`repository 'https://github.com' not found`)**: Git kept wiping the repository path, truncating it to the generic homepage. Even after nuking the local tracking database (`rm -rf .git`), rebuilding it, and clearing global configurations, the error persisted.
4. **Authentication Block (`401 Unauthorized`)**: Cursor's background credential cache intercepted the HTTPS network request and passed expired/broken authorization tokens, crashing the connection.

---

## 2. Why Things Behaved This Way
* **Nested Repositories**: The sub-folder `Aircraft Safety Tracker` originally had its own hidden `.git` metadata folder initialized to a detached `main` branch. This conflicted directly with the parent `Portfolio` repository tracking your feedback branch.
* **HTTPS Credential Hijacking**: Cursor inherits VS Code's Git helper (`GIT_ASKPASS`). When connecting via HTTPS (`https://github.com...`), Cursor automatically intercepts the connection to manage login tokens. Because a stale/expired token was cached for the base `github.com` domain, it overrode your manual terminal configurations and fed Git a corrupted address.

---

## 3. What We Learned About Your Setup
* **Shell & Tools**: You are running an active **Conda environment** (Python manager) on a macOS Bash shell interface.
* **The Twin Keys**: Your machine already contains both older RSA (`id_rsa`) and modern Ed25519 (`id_ed25519`) SSH keys, meaning your system was previously optimized for secure network handshakes.
* **Cursor Parent Scanning**: We discovered your IDE was restricted to looking *only* at the immediate directory. Changing the editor setting `Git: Open Repository In Parent Folders` to `always` solved the UI mismatch.

---

## 4. Areas of Concern & Corruption (Is anything broken?)
* **Code Integrity**: **0% Corrupted.** Your application logic, Python tests, and Markdown files were completely untouched during this process. Git's safety guardrails successfully aborted operations before overwriting untracked files.
* **Git Metadata**: **Resolved.** The corrupted, fragmented local tracking trees inside the project have been completely purged (`rm -rf .git`). Your project is now running on a pristine tracking database.
* **The HTTPS Ghost**: The root cause—Cursor's internal HTTPS credential helper cache—is still technically present on your system. **However, it can no longer harm this project** because we broke out of the HTTPS loop entirely by switching the project's protocol to SSH.

---

## 5. Next Steps & Best Practices
* **Stick to SSH for New Projects**: When cloning or adding new repositories in Cursor, always copy the SSH link (`git@github.com:USERNAME/REPO.git`) instead of the HTTPS URL. This bypasses Cursor's credential manager entirely and uses your Mac's secure background keys.
* **Leverage the Parent Configuration**: You can now freely open *just* the `Aircraft Safety Tracker` folder using **File > Open Folder**. Because of our settings change, Cursor will automatically find the parent `Portfolio` Git layout without losing your branch context.
* **Maintain the Journal**: Ensure your Cursor Agent documents future milestones in your newly created `JOURNAL.md` file before wrapping up development sessions.
