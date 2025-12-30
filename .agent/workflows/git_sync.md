---
description: Stage, commit, and push changes to Git repository
---

1. Check the current status of the repository:
   ```bash
   git status
   ```

2. Generate a concise and descriptive commit message based on the changes. You can use `git diff --cached` or just `git status` context to infer the message. If many files are changed, summarize the main purpose.

3. Stage all changes and commit (or stage selectively if appropriate):
   ```bash
   git add .
   git commit -m "your generated commit message"
   ```

4. Push the changes to the remote repository:
   ```bash
   git push
   ```
