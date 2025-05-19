# 🧬 Repo Merger CLI (Beta)

> ⚠️ This tool is currently in **beta**. Expect bugs, partial implementations, and missing features like `--logfile`.

A powerful, interactive CLI tool to **merge two Git repositories** into one—preserving commit history, filtering subdirectories, resolving conflicts, and offering diff previews, analytics, and semantic merging capabilities.

---

## 📦 Features

* 🔀 Merge two Git repos while keeping commit history intact.
* 🗂️ Merge only specific subdirectories.
* 👀 Preview diffs and logs before merging.
* 🧠 Smart conflict resolution with strategies (`--merge-conflict-base`, `--merge-conflict-side`).
* 📊 Merge analytics and verbose debugging output.
* ⚙️ Interactive prompts for safer merges.

---

## 🚧 Requirements

* Python 3.11+
* Git CLI (`git`) installed
* `git-filter-repo` installed and added to your `PATH`

```bash
pip install git-filter-repo@git+https://github.com/newren/git-filter-repo.git
```

> ✅ Ensure `git-filter-repo` is accessible globally in your terminal. You can verify with:

```bash
git-filter-repo --help
```

---

## 🧪 Current Limitations

* `--logfile` argument exists but is **not yet implemented**.
* Repo must be accessible locally or via URL.
* No auto-retry or rollback yet—manual recovery required if merge fails mid-process.

---

## 📜 Usage

```bash
python repo-merger.py --base <base_repo_url> --side <side_repo_url> --subdir src/module --m "Merge commit" --merge-conflict-base --show-diff --merge-preview -y
```

### ⚙️ CLI Options

| Flag                    | Description                                            |
| ----------------------- | ------------------------------------------------------ |
| `--base`                | Path or URL to the base repository                     |
| `--side`                | Path or URL to the side repository to merge            |
| `--subdir`              | Subdirectory from the side repo to merge               |
| `--m`                   | Commit message for the merge                           |
| `--merge-conflict-base` | Resolve conflicts favoring the base repo (`-X ours`)   |
| `--merge-conflict-side` | Resolve conflicts favoring the side repo (`-X theirs`) |
| `--merge-preview`       | Show logs and tree before merge                        |
| `--show-diff`           | Display diff before merge                              |
| `--smart`               | Enable smart merging strategies (semantic logic WIP)   |
| `--verbose`             | Enable verbose CLI output                              |
| `--debug`               | Show extra debug info                                  |
| `--analytics`           | Print time and operation analytics                     |
| `--logfile <file>`      | (⚠️ **Not yet implemented**) Output logs to a file     |
| `-y`                    | Run non-interactively, auto-confirm all prompts        |

---

## 🚀 Example

```bash
python repo-merger.py \
  --base https://github.com/you/base.git \
  --side https://github.com/you/side.git \
  --subdir src/utils \
  --merge-conflict-base \
  --m "Merge utils from side" \
  --merge-preview --show-diff --verbose --debug --analytics -y
```

---

## 🧼 Clean Up

After a successful merge, remember to:

```bash
git remote remove merge_repo
```

---

## 🛠️ Roadmap

* [ ] `--logfile` full implementation
* [ ] Auto-retry and undo capabilities
* [ ] Merge impact reports
* [ ] Rich TUI/GUI (maybe via `Textual` or `urwid`)
* [ ] Improved subdir conflict mapping

---

## 🧠 License

MIT — but this is a beta prototype. Use at your own risk.

---
