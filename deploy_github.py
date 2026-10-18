#!/usr/bin/env python3
"""
Automated GitHub Sync & Deployment Script for Shorts Studio.
Uses the GitHub REST API (Git Trees & Blobs) to upload and sync
project files and web assets directly to GitHub and GitHub Pages.
"""

import base64
import os
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Installing httpx dependency...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

# --- Configuration ---
PROJECT_ROOT = Path(r"d:\Antigravity.google\ShortsStudio")
TOKEN_FILE = PROJECT_ROOT / ".github_token"

if "GITHUB_TOKEN" in os.environ and os.environ["GITHUB_TOKEN"]:
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
elif TOKEN_FILE.exists():
    GITHUB_TOKEN = TOKEN_FILE.read_text(encoding="utf-8").strip()
else:
    GITHUB_TOKEN = ""

GITHUB_USER = os.environ.get("GITHUB_USER", "ah107gemi")
REPO_NAME = os.environ.get("REPO_NAME", "shorts-studio")
BRANCH = os.environ.get("BRANCH", "main")

# Max file size to upload via Git Trees API (25 MB)
MAX_FILE_SIZE = 25 * 1024 * 1024

# Folders / patterns / files to exclude from GitHub repo
EXCLUDE_DIRS = {
    "venv",
    ".pytest_cache",
    "__pycache__",
    ".git",
    ".trash",
    "bin",         # ~210 MB ffmpeg binaries, inappropriate for web/git
    "temp_video",
}

EXCLUDE_FILES = {
    ".github_token",
    ".env",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".exe",
}

def get_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ShortsStudio-Deployer/1.0",
    }

def collect_files():
    """
    Collect all project files to deploy.
    Also produces GitHub Pages web root assets:
    - Copies frontend/index.html to root index.html (with relative asset paths)
    - Maps frontend/css/ and frontend/js/ so the web app runs directly on GitHub Pages!
    """
    files = {}

    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file():
            continue

        # Check exclusions
        parts = path.relative_to(PROJECT_ROOT).parts
        if any(part in EXCLUDE_DIRS for part in parts):
            continue
        if path.name in EXCLUDE_FILES or any(part in EXCLUDE_FILES for part in parts):
            continue
        if path.suffix.lower() in EXCLUDE_EXTENSIONS:
            continue
        if path.stat().st_size > MAX_FILE_SIZE:
            print(f"Skipping large file (>25MB): {path.name} ({path.stat().st_size / (1024*1024):.1f} MB)")
            continue

        rel_path = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
        try:
            content = path.read_bytes()
            files[rel_path] = content
        except Exception as e:
            print(f"Warning: could not read {rel_path}: {e}")

    # Prepare root files for GitHub Pages deployment
    # 1. Ensure root index.html points to css/ and js/ relatively
    frontend_index = PROJECT_ROOT / "frontend" / "index.html"
    if frontend_index.exists():
        index_html = frontend_index.read_text(encoding="utf-8")
        # Replace leading absolute slash asset paths with relative paths
        index_html = index_html.replace('href="/css/', 'href="css/')
        index_html = index_html.replace('src="/js/', 'src="js/')
        files["index.html"] = index_html.encode("utf-8")

    # 2. Expose css/ and js/ directly at root for GitHub Pages
    for p in (PROJECT_ROOT / "frontend" / "css").rglob("*.css"):
        rel = f"css/{p.name}"
        files[rel] = p.read_bytes()

    for p in (PROJECT_ROOT / "frontend" / "js").rglob("*.js"):
        rel_js = str(p.relative_to(PROJECT_ROOT / "frontend")).replace("\\", "/")
        files[rel_js] = p.read_bytes()

    # 3. Add .nojekyll so GitHub Pages serves _ folders and all files as-is
    files[".nojekyll"] = b""

    return files

def deploy():
    print("=" * 60)
    print(f"🚀 Deploying Shorts Studio to GitHub: {GITHUB_USER}/{REPO_NAME} [{BRANCH}]")
    print("=" * 60)

    client = httpx.Client(headers=get_headers(), timeout=60.0)

    # 1. Verify or create repository
    repo_url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}"
    r = client.get(repo_url)
    if r.status_code == 404:
        print(f"Repository {GITHUB_USER}/{REPO_NAME} does not exist. Creating it now...")
        cr = client.post(
            "https://api.github.com/user/repos",
            json={
                "name": REPO_NAME,
                "description": "Shorts Studio - Complete AI Video Production Pipeline Web App",
                "homepage": f"https://{GITHUB_USER}.github.io/{REPO_NAME}/",
                "private": False,
                "auto_init": True,
            },
        )
        if cr.status_code not in (200, 201):
            print(f"Error creating repository: {cr.status_code} {cr.text}")
            sys.exit(1)
        print("✓ Repository created successfully.")
        time.sleep(2)

    # 2. Get latest commit SHA on target branch
    ref_url = f"{repo_url}/git/refs/heads/{BRANCH}"
    r = client.get(ref_url)
    if r.status_code != 200:
        print(f"Branch {BRANCH} not found. Initializing branch...")
        # Get default branch ref if available
        repo_data = client.get(repo_url).json()
        default_branch = repo_data.get("default_branch", "main")
        r_def = client.get(f"{repo_url}/git/refs/heads/{default_branch}")
        if r_def.status_code == 200:
            latest_commit_sha = r_def.json()["object"]["sha"]
            client.post(f"{repo_url}/git/refs", json={"ref": f"refs/heads/{BRANCH}", "sha": latest_commit_sha})
        else:
            print("Cannot locate base commit. Ensure repo has at least one commit.")
            sys.exit(1)
    else:
        latest_commit_sha = r.json()["object"]["sha"]

    print(f"Base commit: {latest_commit_sha[:8]}")

    # 3. Collect files
    print("Collecting files to deploy...")
    files = collect_files()
    print(f"Found {len(files)} files to sync.")

    # 4. Upload blobs
    tree_items = []
    print("Uploading file blobs to GitHub...")
    for idx, (path, content) in enumerate(files.items(), start=1):
        if idx % 10 == 0 or idx == len(files):
            print(f"  Uploading [{idx}/{len(files)}] {path}...")
        try:
            b64_content = base64.b64encode(content).decode("ascii")
            blob_resp = client.post(
                f"{repo_url}/git/blobs",
                json={"content": b64_content, "encoding": "base64"},
            )
            if blob_resp.status_code not in (200, 201):
                print(f"Error uploading blob for {path}: {blob_resp.text}")
                continue
            blob_sha = blob_resp.json()["sha"]
            tree_items.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            })
        except Exception as e:
            print(f"Error processing {path}: {e}")

    # 5. Create new Git tree
    print("Creating Git Tree...")
    tree_resp = client.post(
        f"{repo_url}/git/trees",
        json={"tree": tree_items},
    )
    if tree_resp.status_code not in (200, 201):
        print(f"Error creating tree: {tree_resp.text}")
        sys.exit(1)
    new_tree_sha = tree_resp.json()["sha"]
    print(f"✓ Git Tree created: {new_tree_sha[:8]}")

    # 6. Create Commit
    print("Creating Commit...")
    commit_msg = f"Auto-sync: update Shorts Studio web assets ({time.strftime('%Y-%m-%d %H:%M:%S')})"
    commit_resp = client.post(
        f"{repo_url}/git/commits",
        json={
            "message": commit_msg,
            "tree": new_tree_sha,
            "parents": [latest_commit_sha],
        },
    )
    if commit_resp.status_code not in (200, 201):
        print(f"Error creating commit: {commit_resp.text}")
        sys.exit(1)
    new_commit_sha = commit_resp.json()["sha"]
    print(f"✓ Commit created: {new_commit_sha[:8]}")

    # 7. Update branch ref
    print(f"Updating branch {BRANCH}...")
    ref_update = client.patch(
        ref_url,
        json={"sha": new_commit_sha, "force": True},
    )
    if ref_update.status_code != 200:
        print(f"Error updating ref: {ref_update.text}")
        sys.exit(1)
    print("✓ Branch reference updated.")

    # 8. Ensure GitHub Pages is active
    pages_url = f"{repo_url}/pages"
    p_check = client.get(pages_url)
    if p_check.status_code == 404:
        print("Enabling GitHub Pages...")
        client.post(pages_url, json={"source": {"branch": BRANCH, "path": "/"}})
    print("✓ GitHub Pages is active.")

    print("\n" + "=" * 60)
    print("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"📦 Repository URL: https://github.com/{GITHUB_USER}/{REPO_NAME}")
    print(f"🌐 GitHub Pages URL: https://{GITHUB_USER}.github.io/{REPO_NAME}/")
    print("=" * 60)

if __name__ == "__main__":
    deploy()
