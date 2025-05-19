import argparse
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

from rich import print
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table

console = Console()
BASE_REPO_DIR = Path("./base_repo").absolute()
MERGE_REPO_DIR = Path("./merge_repo").absolute()
LOGFILE_HANDLE = None
ANALYTICS = []


def log(msg):
    if LOGFILE_HANDLE:
        LOGFILE_HANDLE.write(f"{msg}\n")
    if args.verbose or args.debug:
        print(msg)


def run_cmd(cmd, cwd=None, live_output=False):
    start = time.time()
    result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=not live_output, text=True)
    end = time.time()

    output = result.stdout if not live_output else ""
    if args.analytics:
        ANALYTICS.append({
            "cmd": cmd,
            "success": result.returncode == 0,
            "time": end - start
        })
    if args.debug:
        console.log(f"[DEBUG] Command: {cmd}")
        console.log(f"[DEBUG] Exit Code: {result.returncode}")
        console.log(f"[DEBUG] Output: {output.strip()}")
    if result.returncode != 0:
        console.log(f"[red]Error: {result.stderr.strip()}[/red]")
        raise Exception(f"Command failed: {cmd}")
    return output.strip()


def cleanup():
    for repo in [BASE_REPO_DIR, MERGE_REPO_DIR]:
        if repo.exists():
            def onerror(func, path, _):
                os.chmod(path, stat.S_IWRITE)
                func(path)

            shutil.rmtree(repo, onerror=onerror)


def sigint_handler():
    print("\n[bold red]Aborted by user. Cleaning up...[/bold red]")
    cleanup()
    sys.exit(1)


def check_deps():
    for dep in ["git", "git-filter-repo"]:
        if shutil.which(dep) is None:
            console.print(f"[red]Missing dependency: {dep}[/red]")
            sys.exit(1)


def clone_repo(url, target):
    with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Cloning repo...", total=None)

        process = subprocess.Popen(
            ["git", "clone", "--progress", url, target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        for line in process.stderr:
            if "%" in line:
                progress.update(task, advance=1)
        process.wait()
        progress.update(task, completed=100)

    return process.returncode


def list_branches(repo_dir):
    raw = run_cmd("git branch -r", cwd=repo_dir)
    branches = [line.strip().split("/")[-1] for line in raw.splitlines()
                if "->" not in line and "HEAD" not in line]
    return sorted(set(branches))


def get_head_branch(repo_dir):
    try:
        output = run_cmd("git remote show origin", cwd=repo_dir)
        for line in output.splitlines():
            if "HEAD branch:" in line:
                return line.split(":")[1].strip()
            return None
        return None
    except Exception:
        return "main"


def filter_repo_to_subdir(repo_dir_, subdir_):
    try:
        run_cmd(f"git-filter-repo --to-subdirectory-filter {subdir_} --force", cwd=repo_dir_)
    except Exception as e:
        console.print(f"{e}")
        exit(1)


def open_dir(path):
    if os.name == "nt":
        os.startfile(path)


def get_commit_dates(repo_dir, branches):
    results = {}
    for b in branches:
        try:
            date = run_cmd(f"git log origin/{b} -1 --format=%ci", cwd=repo_dir)
            results[b] = date
        except Exception:
            results[b] = "N/A"
    return results


def choose_branch(repo_dir):
    branches = list_branches(repo_dir)
    head = get_head_branch(repo_dir)
    dates = get_commit_dates(repo_dir, branches)

    table = Table(title="Available Branches", show_lines=True)
    table.add_column("Branch")
    table.add_column("Last Commit Date")

    for b in branches:
        table.add_row(b, dates[b])
    console.print(table)

    default = head if head in branches else branches[0]
    return Prompt.ask("Select branch to merge", choices=branches, default=default)


def perform_merge(base_branch_, subdir_, conflict_strategy):
    run_cmd(f"git checkout {base_branch_}", cwd=BASE_REPO_DIR)
    run_cmd("git remote add merge_repo ../merge_repo", cwd=BASE_REPO_DIR)
    run_cmd("git fetch merge_repo", cwd=BASE_REPO_DIR)

    if args.merge_preview:
        run_cmd("git log --graph --oneline --all", cwd=BASE_REPO_DIR)
        run_cmd("git ls-tree -r HEAD", cwd=BASE_REPO_DIR)
        return

    if args.show_diff and Prompt.ask("Show diff before merge?", choices=["yes", "no"]) == "yes":
        run_cmd("git diff HEAD merge_repo/HEAD", cwd=BASE_REPO_DIR, live_output=True)

    strategy_flag = ""
    if conflict_strategy == "base":
        strategy_flag = "-X ours"
    elif conflict_strategy == "side":
        strategy_flag = "-X theirs"

    base_merge_cmd = f"git merge merge_repo/HEAD --allow-unrelated-histories {strategy_flag}"

    try:
        run_cmd(base_merge_cmd.strip(), cwd=BASE_REPO_DIR, live_output=True)
    except Exception as e:
        if "unrelated histories" in str(e).lower():
            # Fallback already handled above, but in case Git behaves weirdly
            run_cmd(f"git merge merge_repo/HEAD --allow-unrelated-histories {strategy_flag}".strip(), cwd=BASE_REPO_DIR, live_output=True)
        else:
            print(f"[yellow]Merge conflict occurred while merging into '{subdir_}'[/yellow]")

            if args.merge_conflict_side:
                run_cmd(f"git merge --strategy=recursive -X theirs merge_repo/HEAD", cwd=BASE_REPO_DIR, live_output=True)
            elif args.merge_conflict_base:
                run_cmd(f"git merge --strategy=recursive -X ours merge_repo/HEAD", cwd=BASE_REPO_DIR, live_output=True)
            elif args.y:
                pass  # Skip prompt
            else:
                open_dir(BASE_REPO_DIR)
                Prompt.ask("Resolve conflicts in subdir '{subdir_}' then press Enter")


def show_git_stat():
    if args.verbose:
        print("[bold blue]Merge Summary:[/bold blue]")
        run_cmd("git diff --stat", cwd=BASE_REPO_DIR, live_output=True)


def print_analytics():
    if not args.analytics:
        return
    table = Table(title="Analytics", show_lines=True)
    table.add_column("Command")
    table.add_column("Time (s)")
    table.add_column("Success")

    for entry in ANALYTICS:
        table.add_row(entry["cmd"], f"{entry['time']:.2f}", "✅ " if entry["success"] else "❌")
    console.print(table)


# --- ARGPARSE ---

parser = argparse.ArgumentParser(description="🧠 Git Merge Tool with Subdir Filtering and Conflict Strategies")
parser.add_argument("--verbose", action="store_true")
parser.add_argument("--debug", action="store_true")
parser.add_argument("--analytics", action="store_true")
parser.add_argument("--logfile", type=str, help="Log file name")
parser.add_argument("--retry", action="store_true")
parser.add_argument("--merge-conflict-base", action="store_true")
parser.add_argument("--merge-conflict-side", action="store_true")
parser.add_argument("--merge-preview", action="store_true")
parser.add_argument("--show-diff", action="store_true")
parser.add_argument("--smart", action="store_true")
parser.add_argument("-y", action="store_true", help="Auto accept all prompts")
parser.add_argument("--base-branch", type=str, help="Base branch to merge into")

args = parser.parse_args()
if args.logfile:
    LOGFILE_HANDLE = open(args.logfile, "w", encoding="utf-8")
if args.merge_conflict_base and args.merge_conflict_side:
    print("[red]Cannot use both --merge-conflict-base and --merge-conflict-side[/red]")
    sys.exit(1)

signal.signal(signal.SIGINT, sigint_handler)
check_deps()

SUCCESS = False
GITMERGE_BASE = os.environ.get("GITMERGE_BASE", None)
GITMERGE_MERGE = os.environ.get("GITMERGE_MERGE", None)

try:
    if not args.retry:
        cleanup()

    # --- PROMPTS ---

    base_url = Prompt.ask("Base repo URL") if not GITMERGE_BASE else GITMERGE_BASE
    merge_url = Prompt.ask("Repo to merge in") if not GITMERGE_MERGE else GITMERGE_MERGE
    subdir = Prompt.ask("Subdirectory to move merged code into") if not args.y else "merged_content"

    # --- CLONE & PREP ---
    clone_repo(base_url, BASE_REPO_DIR)
    clone_repo(merge_url, MERGE_REPO_DIR)

    merge_branch = choose_branch(MERGE_REPO_DIR)
    run_cmd(f"git checkout {merge_branch}", cwd=MERGE_REPO_DIR)
    filter_repo_to_subdir(MERGE_REPO_DIR, subdir)

    base_branch = args.base_branch or Prompt.ask("Target branch to merge into", default="main")
    perform_merge(base_branch, subdir,
                  "base" if args.merge_conflict_base else "side" if args.merge_conflict_side else None)

    show_git_stat()

    if Prompt.ask("Push to origin?", choices=["yes", "no"], default="no") == "yes":
        run_cmd("git push origin HEAD", cwd=BASE_REPO_DIR)

    print_analytics()

    SUCCESS = True
finally:
    if LOGFILE_HANDLE:
        LOGFILE_HANDLE.close()
    if not SUCCESS:
        cleanup()
