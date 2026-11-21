#!/usr/bin/env python3
"""Fail-closed GitHub REST publisher for the curated arcade audit export."""
import argparse
import base64
import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import sys
import tarfile
import time
import urllib.error
import urllib.request

OWNER = "agustinc08"
REPO = "arcade-audit"
BRANCH = "main"
BASE_URL = "https://api.github.com"
EXPECTED_INITIAL_HEAD = "e240c0c68951ef508e15110e467721a1b24ba04f"
API_VERSION = "2022-11-28"
USER_AGENT = "Batocera-Arcade-Audit"
AUDIT = pathlib.Path("/userdata/system/state/arcade_audit")
EXPORT = pathlib.Path("/userdata/system/state/arcade_audit_git")
TOOLS = pathlib.Path("/userdata/system/el_gordo_tools")
TOKEN_FILE = pathlib.Path("/userdata/system/secrets/github_arcade_audit.token")
STATE_FILE = AUDIT / "github_publish_state.json"
EXPORT_MANIFEST = AUDIT / "github_export_manifest.json"
ONE_TIME_MANIFEST = AUDIT / "github_one_time_changeset_approval.json"
ALLOWED_ROOT_FILES = {"README.md", ".gitignore", "ARCADE_CURRENT_STATE.md", "ARCADE_DOCUMENT_INDEX.md",
                      "CODEX_NEXT_TASK.md", "MANUAL_NEXT_TASK.md", "autopilot_state.json"}
ALLOWED_DIRS = {"data", "reports", "scripts", "docs"}
EXPORT_SCOPES = {"all", "autopilot-infrastructure", "incident-batch"}
EXPORT_SCOPE_PATHS = {
    "autopilot-infrastructure": {
        "CODEX_NEXT_TASK.md", "MANUAL_NEXT_TASK.md", "autopilot_state.json",
        "data/autopilot_tasks.json", "docs/ARCADE_AUTOPILOT.md",
        "docs/CERTIFIER_JOB_RUNNER.md", "reports/AUTOPILOT_STATUS.md",
        "reports/AUTOPILOT_OWNER_HANDOFF.md",
    },
    "incident-batch": {
        "ARCADE_CURRENT_STATE.md", "data/arcade_issues.csv",
        "data/autopilot_tasks.json", "autopilot_state.json",
        "data/arcade_master_checkpoint.json", "data/controllers_live.json",
        "data/full_game_certification.csv", "data/full_game_certification_checkpoint.json",
        "reports/AUTOPILOT_STATUS.md", "reports/CERTIFIER_MARKER_COLLISION.md",
        "reports/CURRENT_BATOCERA_CONFIG.md", "reports/FULL_GAME_CERTIFICATION_SUMMARY.md",
        "reports/PRIORITY_CERTIFICATION_BATCH_59.md", "reports/ROOT_CAUSES.md",
        "scripts/active/full_game_certifier.py",
        "scripts/active/rebuild_arcade_current_state.py",
        "scripts/active/rebuild_certification_summary.py",
        "scripts/active/rebuild_priority_batch_report.py",
        "scripts/active/certification_batch_accounting.py",
        "scripts/active/arcade_autopilot.py",
        "scripts/active/publish_arcade_audit_github.py",
        "scripts/tests/test_batch59_reconciliation.py",
        "scripts/tests/test_arcade_autopilot.py",
    },
}
ALLOWED_SUFFIXES = {".md", ".txt", ".csv", ".json", ".py", ".sh"}
DOC_SUFFIXES = {".md", ".txt"}
EXCLUDED_SOURCE_NAMES = {"GIT_BATOCERA_SETUP.md", "GITHUB_API_PUBLISHER_SETUP.md",
                         "github_publish_state.json", "github_export_manifest.json",
                         "github_one_time_changeset_approval.json"}
SCRUB_KEYS = {"launcher_log", "emulator_log", "effective_config", "logs_pre", "logs_post",
              "logs_observed", "config_copy", "pre_snapshot"}
FORBIDDEN_SUFFIXES = {
    ".zip", ".7z", ".rar", ".chd", ".iso", ".bin", ".cue", ".gdi", ".cso", ".rvz",
    ".wbfs", ".nsp", ".xci", ".sav", ".srm", ".state", ".mp4", ".mkv", ".avi", ".mov",
    ".png", ".jpg", ".jpeg", ".webp"
}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024
MAX_CHANGED_FILES = 20
MAX_CHANGESET_FRACTION = 0.50
MAX_DELETES = 20
MAX_DELETE_FRACTION = 0.25
MIN_RATE_REMAINING = 10
TOKEN_PREFIX = "github_pat_"


class PublishError(Exception):
    def __init__(self, category, detail=""):
        super().__init__(category)
        self.category = category
        self.detail = detail


def say(value):
    print(value, flush=True)


def safe_path(path):
    return path.as_posix()


def allowed_repo_path(path):
    if path in ALLOWED_ROOT_FILES:
        return True
    return any(path.startswith(prefix + "/") for prefix in ALLOWED_DIRS)


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def scrub_checkpoint(value):
    if isinstance(value, dict):
        return {k: scrub_checkpoint(v) for k, v in value.items() if k.lower() not in SCRUB_KEYS}
    if isinstance(value, list):
        return [scrub_checkpoint(v) for v in value]
    return value


def source_export_map():
    if not AUDIT.is_dir() or AUDIT.is_symlink():
        raise PublishError("EXPORT_SYNC_FAIL", "active audit directory unavailable")
    found = {}
    for p in AUDIT.iterdir():
        if not p.is_file() or p.is_symlink() or p.name in EXCLUDED_SOURCE_NAMES:
            continue
        suffix = p.suffix.lower()
        if suffix not in ALLOWED_SUFFIXES or ".pre_failure_analysis" in p.name.lower() or "backup_path" in p.name.lower():
            continue
        if any(word in p.name.lower() for word in ("credential", "secret", "token")):
            continue
        if p.name in {"ARCADE_CURRENT_STATE.md", "ARCADE_DOCUMENT_INDEX.md", "CODEX_NEXT_TASK.md",
                      "MANUAL_NEXT_TASK.md"}:
            found[p.name] = p
            continue
        if p.name == "autopilot_state.json":
            found[p.name] = p
            continue
        parent = {".md": "reports", ".txt": "reports", ".csv": "data", ".json": "data",
                  ".py": "scripts", ".sh": "scripts"}[suffix]
        found[parent + "/" + p.name] = p
    # The active audit keeps structured inventories under data/. Preserve the
    # legacy root-level mapping above, but prefer the canonical nested file
    # when both locations map to the same repository path.
    data_dir = AUDIT / "data"
    if data_dir.is_dir() and not data_dir.is_symlink():
        for p in data_dir.rglob("*"):
            if p.is_symlink():
                raise PublishError("EXPORT_SYNC_FAIL", "symlink found in approved source data")
            if not p.is_file() or p.suffix.lower() not in (".csv", ".json"):
                continue
            if any(word in p.name.lower() for word in ("credential", "secret", "token")):
                continue
            rel = "data/" + p.relative_to(data_dir).as_posix()
            found[rel] = p
    scripts = AUDIT / "scripts"
    if scripts.is_dir() and not scripts.is_symlink():
        for p in scripts.rglob("*"):
            if p.is_symlink():
                raise PublishError("EXPORT_SYNC_FAIL", "symlink found in approved source scripts")
            if p.is_file() and p.suffix.lower() in (".py", ".sh"):
                rel = "scripts/" + p.relative_to(scripts).as_posix()
                found[rel] = p
    # Export only the reviewed active job and Autopilot entrypoints, never runtime state.
    for source, rel in (
        (TOOLS / "arcade_autopilot.py", "scripts/active/arcade_autopilot.py"),
        (TOOLS / "arcade_autopilot", "scripts/active/arcade_autopilot.sh"),
        (TOOLS / "arcade_certifier_job.py", "scripts/active/arcade_certifier_job.py"),
        (TOOLS / "arcade_certifier_job.sh", "scripts/active/arcade_certifier_job.sh"),
        (TOOLS / "full_game_certifier.py", "scripts/active/full_game_certifier.py"),
        (TOOLS / "rebuild_arcade_current_state.py", "scripts/active/rebuild_arcade_current_state.py"),
        (TOOLS / "rebuild_certification_summary.py", "scripts/active/rebuild_certification_summary.py"),
        (TOOLS / "rebuild_priority_batch_report.py", "scripts/active/rebuild_priority_batch_report.py"),
        (TOOLS / "certification_batch_accounting.py", "scripts/active/certification_batch_accounting.py"),
        (TOOLS / "arcade_autopilot.py", "scripts/active/arcade_autopilot.py"),
        (TOOLS / "publish_arcade_audit_github.py", "scripts/active/publish_arcade_audit_github.py"),
        (AUDIT / "tests" / "test_batch59_reconciliation.py", "scripts/tests/test_batch59_reconciliation.py"),
        (TOOLS / "marker_ownership.py", "scripts/active/marker_ownership.py"),
    ):
        if source.is_file() and not source.is_symlink():
            found[rel] = source
    for root in ("reports", "docs"):
        directory = AUDIT / root
        if directory.is_dir() and not directory.is_symlink():
            for p in directory.rglob("*"):
                if p.is_symlink():
                    raise PublishError("EXPORT_SYNC_FAIL", f"symlink found in approved source {root}")
                if p.is_file() and p.suffix.lower() in DOC_SUFFIXES:
                    rel = root + "/" + p.relative_to(directory).as_posix()
                    # The batch certification reports also exist under the
                    # historical reports/certification/ names. When the
                    # canonical PRIORITY_CERTIFICATION_BATCH_N.md is present
                    # with identical content, export only that canonical copy.
                    if root == "reports" and p.parent == directory / "certification":
                        name = p.name
                        if name.startswith("PRIORITY_BATCH_") and name.endswith(".md"):
                            batch_id = name[len("PRIORITY_BATCH_"):-len(".md")]
                            canonical_candidates = (
                                AUDIT / f"PRIORITY_CERTIFICATION_BATCH_{batch_id}.md",
                                AUDIT / "reports" / f"PRIORITY_CERTIFICATION_BATCH_{batch_id}.md",
                            )
                            canonical = next((candidate for candidate in canonical_candidates
                                              if candidate.is_file() and not candidate.is_symlink()), None)
                            if canonical is not None and canonical.read_bytes() == p.read_bytes():
                                continue
                    found[rel] = p
    return found


def export_files():
    if not EXPORT.is_dir() or EXPORT.is_symlink():
        raise PublishError("EXPORT_SYNC_FAIL", "export directory unavailable")
    for p in EXPORT.iterdir():
        if p.name == ".git":
            # A pre-existing audit manifest directory is preserved but never published.
            if p.is_symlink() or not p.is_dir():
                raise PublishError("EXPORT_SYNC_FAIL", "unexpected .git path")
            if (p / "HEAD").exists() or (p / "config").exists() or (p / "objects").exists():
                raise PublishError("EXPORT_SYNC_FAIL", "Git metadata is forbidden in the export")
            continue
        if p.name in ALLOWED_ROOT_FILES and p.is_file() and not p.is_symlink():
            continue
        if p.name in ALLOWED_DIRS and p.is_dir() and not p.is_symlink():
            continue
        raise PublishError("PAYLOAD_SCAN_FAIL", "unapproved item at export root")
    paths = {}
    for root in ALLOWED_DIRS:
        directory = EXPORT / root
        if not directory.exists():
            continue
        for p in directory.rglob("*"):
            if p.is_symlink():
                raise PublishError("PAYLOAD_SCAN_FAIL", "symlink in export")
            if p.is_dir():
                continue
            rel = p.relative_to(EXPORT).as_posix()
            if not allowed_repo_path(rel) or p.suffix.lower() not in ALLOWED_SUFFIXES:
                raise PublishError("PAYLOAD_SCAN_FAIL", "unapproved file in export")
            if rel.startswith("docs/") and p.suffix.lower() not in DOC_SUFFIXES:
                raise PublishError("PAYLOAD_SCAN_FAIL", "non-document file in docs/")
            paths[rel] = p
    for name in ALLOWED_ROOT_FILES:
        p = EXPORT / name
        if p.exists():
            if not p.is_file() or p.is_symlink():
                raise PublishError("PAYLOAD_SCAN_FAIL", "invalid approved root file")
            paths[name] = p
    return paths


def in_export_scope(rel, scope):
    if scope == "all":
        return True
    if scope == "autopilot-infrastructure":
        return (rel in EXPORT_SCOPE_PATHS[scope] or rel.startswith("scripts/") or
                rel.startswith("docs/"))
    return rel in EXPORT_SCOPE_PATHS[scope]


def sync_export(scope="all"):
    if scope not in EXPORT_SCOPES:
        raise PublishError("EXPORT_SYNC_FAIL", "unknown export scope")
    source = source_export_map()
    if not (EXPORT / "README.md").is_file() or not (EXPORT / ".gitignore").is_file():
        raise PublishError("EXPORT_SYNC_FAIL", "README.md or .gitignore missing from curated export")
    previous = set()
    if EXPORT_MANIFEST.exists():
        try:
            doc = json.loads(EXPORT_MANIFEST.read_text(encoding="utf-8"))
            previous = {p for p in doc.get("files", []) if isinstance(p, str) and allowed_repo_path(p)}
        except Exception:
            raise PublishError("EXPORT_SYNC_FAIL", "local export manifest is invalid")
    else:
        previous = {p for p in export_files() if allowed_repo_path(p)}
    added, modified, removed = [], [], []
    for rel, src in sorted(source.items()):
        if not in_export_scope(rel, scope):
            continue
        if rel in {"README.md", ".gitignore"}:
            continue
        data = src.read_bytes()
        if src.suffix.lower() == ".json" and "checkpoint" in src.name.lower():
            try:
                obj = json.loads(data.decode("utf-8"))
                data = (json.dumps(scrub_checkpoint(obj), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            except Exception:
                raise PublishError("EXPORT_SYNC_FAIL", "checkpoint JSON is invalid UTF-8 JSON")
        if rel == "autopilot_state.json":
            try:
                obj = json.loads(data.decode("utf-8"))
                public_keys = {"schema_version", "status", "started_at", "updated_at", "current_task",
                               "last_completed_task", "safe_mode", "pause_reason", "batches_completed",
                               "games_processed_this_run", "last_github_sha", "next_action"}
                data = (json.dumps({k: v for k, v in obj.items() if k in public_keys},
                                   ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            except Exception:
                raise PublishError("EXPORT_SYNC_FAIL", "Autopilot state is invalid UTF-8 JSON")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise PublishError("EXPORT_SYNC_FAIL", "approved source file is not UTF-8 text")
        target = EXPORT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        old = target.read_bytes() if target.is_file() and not target.is_symlink() else None
        if old == data:
            continue
        tmp = target.with_name(target.name + ".publish.tmp")
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
        (added if old is None else modified).append(rel)
    for rel in sorted(previous - set(source)):
        if not in_export_scope(rel, scope):
            continue
        if rel in {"README.md", ".gitignore"}:
            # These curated export root files are maintained separately.
            continue
        target = EXPORT / rel
        if target.is_file() and not target.is_symlink():
            target.unlink()
            removed.append(rel)
    current = sorted(p for p in export_files() if allowed_repo_path(p))
    atomic_json(EXPORT_MANIFEST, {"repository": OWNER + "/" + REPO, "files": current,
                                 "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    return {"added": added, "modified": modified, "deleted": removed,
            "unchanged": len(current) - len(added) - len(modified), "scope": scope}


TOKEN_PATTERNS = [
    ("GITHUB_TOKEN", re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b")),
    ("BEARER_TOKEN", re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("AUTHORIZATION_HEADER", re.compile(r"(?i)\bAuthorization\s*:\s*\S+")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----")),
    ("SECRET_ASSIGNMENT", re.compile(r"(?i)(?:^|[^A-Za-z0-9_])(?:password|passwd|secret|api[_-]?key|apikey)\s*[:=]\s*[\"']?[^\s\"']{8,}")),
    ("TOKEN_ASSIGNMENT", re.compile(r"(?i)(?:^|[^A-Za-z0-9_])token\s*[:=]\s*[\"']?[^\s\"']{16,}")),
    ("WIFI_CREDENTIAL", re.compile(r"(?i)(?:ssid|wifi[_ -]?(?:password|passwd|key|psk))\s*[:=]\s*[\"']?[^\s\"']{4,}")),
]


def secret_scan(files, token=None):
    total = 0
    findings = []
    secret_root = pathlib.Path("/userdata/system/secrets").resolve()
    for rel, path in sorted(files.items()):
        if re.search(r"(?i)(password|passwd|token|secret|api[_-]?key|wifi|ssid|screenscraper|credential)", rel):
            findings.append((rel, 1, "SENSITIVE_FILENAME"))
            continue
        if secret_root == path.resolve() or secret_root in path.resolve().parents:
            findings.append((rel, 1, "SECRETS_PATH"))
            continue
        data = path.read_bytes()
        total += len(data)
        if token and token.encode("utf-8") in data:
            findings.append((rel, 1, "LOCAL_TOKEN_LEAK"))
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append((rel, 1, "NON_TEXT_SECRET_SCAN"))
            continue
        for number, line in enumerate(content.splitlines(), 1):
            kinds = [name for name, pattern in TOKEN_PATTERNS if pattern.search(line)]
            low = line.lower()
            if "screenscraper" in low and re.search(r"(?i)(?:login|password|passwd|token|api[_-]?key)\s*[:=]\s*[^\s]{5,}", line):
                kinds.append("SCREENSCRAPER_CREDENTIAL")
            for kind in sorted(set(kinds)):
                findings.append((rel, number, kind))
    if findings:
        say("SECRET_SCAN_FAIL")
        for rel, number, kind in findings[:100]:
            say(f"{rel}:{number}: {kind}")
        raise PublishError("SECRET_SCAN_FAIL")
    return total


def payload_scan(files):
    total = 0
    for rel, path in sorted(files.items()):
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise PublishError("PAYLOAD_SCAN_FAIL", "forbidden extension in export")
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise PublishError("PAYLOAD_SCAN_FAIL", "single file exceeds 20 MiB")
        data = path.read_bytes()
        total += size
        if data.startswith((b"PK\x03\x04", b"MComprHD", b"CD001")):
            raise PublishError("PAYLOAD_SCAN_FAIL", "payload signature detected")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise PublishError("PAYLOAD_SCAN_FAIL", "non-text file detected")
    if total > MAX_TOTAL_BYTES:
        raise PublishError("PAYLOAD_SCAN_FAIL", "total export exceeds 50 MiB")
    return total


def load_token(required=False):
    if not TOKEN_FILE.exists():
        if required:
            raise PublishError("WAITING_FOR_GITHUB_TOKEN")
        return None
    if TOKEN_FILE.is_symlink() or not TOKEN_FILE.is_file():
        raise PublishError("AUTH_FAILED", "token path is not a regular file")
    mode = TOKEN_FILE.stat().st_mode & 0o777
    if mode & 0o077:
        raise PublishError("AUTH_FAILED", "token file permissions must be 600 or stricter")
    credential_bytes = TOKEN_FILE.read_bytes()
    credential_value = credential_bytes.decode("utf-8").strip()
    # Calculate the token file digest only in memory. Never log, persist, or transmit it.
    _private_token_file_digest = hashlib.sha256(credential_bytes).digest()
    if not credential_value or not credential_value.startswith(TOKEN_PREFIX) or "\n" in credential_value or "\r" in credential_value:
        raise PublishError("AUTH_FAILED", "token format is not an accepted fine-grained PAT")
    return credential_value


def request(method, endpoint, token=None, body=None, retries=2, raw=False):
    url = endpoint if endpoint.startswith("https://") else BASE_URL + endpoint
    if not url.startswith("https://api.github.com/") and not url.startswith("https://api.github.com"):
        raise PublishError("API_FAILED", "non-API URL rejected")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION,
               "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    transient = {408, 429, 500, 502, 503, 504}
    attempts = retries if method == "GET" or endpoint.endswith("/git/blobs") or endpoint.endswith("/git/trees") or endpoint.endswith("/git/commits") else 1
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read(MAX_TOTAL_BYTES + 1)
                if len(content) > MAX_TOTAL_BYTES:
                    raise PublishError("API_FAILED", "API response exceeds the bounded read size")
                if raw:
                    return resp.status, content, dict(resp.headers.items())
                try:
                    return resp.status, json.loads(content.decode("utf-8")), dict(resp.headers.items())
                except Exception:
                    raise PublishError("API_FAILED", "API returned invalid JSON")
        except urllib.error.HTTPError as e:
            code = e.code
            if code in transient and attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 3))
                continue
            if code == 401:
                category = "AUTH_FAILED"
            elif code == 403:
                remaining = e.headers.get("X-RateLimit-Remaining") if e.headers else None
                retry_after = e.headers.get("Retry-After") if e.headers else None
                category = "RATE_LIMIT_LOW" if remaining == "0" or retry_after else "AUTH_FAILED"
            elif code in (409, 422):
                category = "API_FAILED"
            elif code == 404:
                category = "REMOTE_CHANGED" if "/git/ref/heads/" in endpoint else "API_FAILED"
            elif code in transient:
                category = "NETWORK_FAILED"
            else:
                category = "API_FAILED"
            raise PublishError(category, "HTTP " + str(code))
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt + 1 < attempts and method == "GET":
                time.sleep(min(2 ** attempt, 3))
                continue
            raise PublishError("NETWORK_FAILED")
    raise PublishError("NETWORK_FAILED")


def get_rate(token):
    _, data, headers = request("GET", "/rate_limit", token)
    try:
        return int(data["resources"]["core"]["remaining"]), int(data["resources"]["core"]["limit"])
    except Exception:
        raise PublishError("API_FAILED", "rate-limit response was incomplete")


def get_head(token):
    _, data, _ = request("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}", token)
    sha = data.get("object", {}).get("sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise PublishError("API_FAILED", "branch ref did not contain a commit SHA")
    return sha


def get_remote_tree(token, head):
    _, commit, _ = request("GET", f"/repos/{OWNER}/{REPO}/git/commits/{head}", token)
    tree_sha = commit.get("tree", {}).get("sha")
    if not isinstance(tree_sha, str):
        raise PublishError("API_FAILED", "remote commit tree missing")
    _, tree, _ = request("GET", f"/repos/{OWNER}/{REPO}/git/trees/{tree_sha}?recursive=1", token)
    if tree.get("truncated"):
        raise PublishError("API_FAILED", "remote tree was truncated")
    mapping = {}
    for entry in tree.get("tree", []):
        path = entry.get("path")
        if entry.get("type") == "blob" and isinstance(path, str) and allowed_repo_path(path):
            mapping[path] = entry.get("sha")
    return tree_sha, mapping


def remote_archive(head):
    # The repository is public. Do not send the PAT through a cross-host redirect.
    url = f"{BASE_URL}/repos/{OWNER}/{REPO}/tarball/{head}"
    status, payload, _ = request("GET", url, token=None, retries=2, raw=True)
    if status != 200:
        raise PublishError("API_FAILED", "remote archive request failed")
    try:
        archive = tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz")
        files = {}
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise PublishError("API_FAILED", "remote archive contains a non-regular entry")
            parts = pathlib.PurePosixPath(member.name).parts
            if len(parts) < 2:
                raise PublishError("API_FAILED", "remote archive path is invalid")
            rel = "/".join(parts[1:])
            if not allowed_repo_path(rel):
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise PublishError("API_FAILED", "remote archive entry unavailable")
            data = stream.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise PublishError("PAYLOAD_SCAN_FAIL", "remote file exceeds 20 MiB")
            files[rel] = data
        return files
    except PublishError:
        raise
    except Exception:
        raise PublishError("API_FAILED", "remote archive could not be parsed")


def load_state():
    if not STATE_FILE.exists():
        return None
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        raise PublishError("REMOTE_CHANGED", "publisher state JSON is invalid")
    if state.get("repository") != OWNER + "/" + REPO or state.get("branch") != BRANCH:
        raise PublishError("REMOTE_CHANGED", "publisher state targets a different repository")
    last = state.get("last_known_remote_sha")
    if not isinstance(last, str) or not re.fullmatch(r"[0-9a-f]{40}", last):
        raise PublishError("REMOTE_CHANGED", "publisher state SHA is invalid")
    return state


def establish_head(token):
    head = get_head(token)
    state = load_state()
    if state is None:
        if head != EXPECTED_INITIAL_HEAD:
            raise PublishError("REMOTE_CHANGED", "initial remote HEAD does not match the known BATCH 5 commit")
        state = {"repository": OWNER + "/" + REPO, "branch": BRANCH,
                 "last_known_remote_sha": head, "last_successful_publish_sha": None,
                 "last_publish_at": None}
        atomic_json(STATE_FILE, state)
    elif head != state["last_known_remote_sha"]:
        raise PublishError("REMOTE_CHANGED", "remote HEAD differs from last known state")
    return head, state


def canonical_json_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def one_time_manifest_entries(added, modified, deleted, local, remote_files):
    entries = []
    for status, paths in (("ADDED", added), ("MODIFIED", modified), ("DELETED", deleted)):
        for rel in paths:
            if status == "DELETED":
                data = remote_files.get(rel)
                if data is None:
                    raise PublishError("API_FAILED", "remote deleted-file bytes unavailable")
            else:
                data = local[rel]
            entries.append({"path": rel, "status": status, "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()})
    return sorted(entries, key=lambda x: (x["status"], x["path"]))


def validate_one_time_manifest(head, added, modified, deleted, local, remote_files):
    if ONE_TIME_MANIFEST.is_symlink() or not ONE_TIME_MANIFEST.is_file():
        raise PublishError("LARGE_CHANGESET", "one-time approval manifest is missing or unsafe")
    if ONE_TIME_MANIFEST.stat().st_mode & 0o077:
        raise PublishError("LARGE_CHANGESET", "one-time approval manifest permissions must be 600")
    try:
        doc = json.loads(ONE_TIME_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        raise PublishError("LARGE_CHANGESET", "one-time approval manifest is invalid")
    claimed = doc.get("manifest_sha256")
    unsigned = {k: v for k, v in doc.items() if k != "manifest_sha256"}
    if not isinstance(claimed, str) or canonical_json_sha(unsigned) != claimed:
        raise PublishError("LARGE_CHANGESET", "one-time approval manifest digest mismatch")
    if (doc.get("schema_version") != 1 or doc.get("repository") != OWNER + "/" + REPO
            or doc.get("branch") != BRANCH or doc.get("approved") is not True
            or doc.get("consumed") is not False or doc.get("remote_head") != head):
        raise PublishError("LARGE_CHANGESET", "one-time approval scope does not match repository, branch, state or HEAD")
    try:
        approved_at = datetime.datetime.fromisoformat(doc["approved_at"].replace("Z", "+00:00"))
        age = (datetime.datetime.now(datetime.timezone.utc) - approved_at).total_seconds()
    except Exception:
        raise PublishError("LARGE_CHANGESET", "one-time approval timestamp is invalid")
    if age < 0 or age > 86400:
        raise PublishError("LARGE_CHANGESET", "one-time approval expired")
    actual = one_time_manifest_entries(added, modified, deleted, local, remote_files)
    if doc.get("entries") != actual:
        raise PublishError("LARGE_CHANGESET", "current changed paths or content differ from one-time approval")
    return {"path": str(ONE_TIME_MANIFEST), "manifest_sha256": claimed}


def consume_one_time_manifest(meta):
    path = pathlib.Path(meta["path"])
    doc = json.loads(path.read_text(encoding="utf-8"))
    unsigned = {k: v for k, v in doc.items() if k != "manifest_sha256"}
    if canonical_json_sha(unsigned) != meta["manifest_sha256"] or doc.get("consumed") is not False:
        raise PublishError("LARGE_CHANGESET", "one-time approval changed before consumption")
    doc["consumed"] = True
    doc["consumed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    doc.pop("manifest_sha256", None)
    doc["manifest_sha256"] = canonical_json_sha({k: v for k, v in doc.items() if k != "manifest_sha256"})
    atomic_json(path, doc)


def scan_and_diff(token, require_token=False, one_time_approved=False):
    files = export_files()
    pat = token
    secret_scan(files, pat)
    total = payload_scan(files)
    remaining, limit = get_rate(token)
    if remaining < MIN_RATE_REMAINING:
        raise PublishError("RATE_LIMIT_LOW")
    head, state = establish_head(token)
    tree_sha, remote_blobs = get_remote_tree(token, head)
    remote_files = remote_archive(head)
    local = {rel: p.read_bytes() for rel, p in files.items()}
    local_hash = {rel: hashlib.sha256(data).hexdigest() for rel, data in local.items()}
    added = sorted(set(local) - set(remote_blobs))
    deleted = sorted(set(remote_blobs) - set(local))
    modified, unchanged = [], []
    for rel in sorted(set(local) & set(remote_blobs)):
        if rel not in remote_files:
            raise PublishError("API_FAILED", "remote file tree/archive disagreement")
        remote_digest = hashlib.sha256(remote_files[rel]).hexdigest()
        if local_hash[rel] == remote_digest and local[rel] == remote_files[rel]:
            unchanged.append(rel)
        else:
            modified.append(rel)
    for rel in set(remote_files) - set(remote_blobs):
        raise PublishError("API_FAILED", "remote archive/tree disagreement")
    changed_count = len(added) + len(modified) + len(deleted)
    allowed_existing = len(remote_blobs)
    if len(deleted) > MAX_DELETES or (allowed_existing and len(deleted) / allowed_existing > MAX_DELETE_FRACTION):
        raise PublishError("MASS_DELETE_GUARD")
    basis = max(len(remote_blobs), len(local), 1)
    approval = None
    if one_time_approved:
        approval = validate_one_time_manifest(head, added, modified, deleted, local, remote_files)
    elif changed_count > MAX_CHANGED_FILES or changed_count / basis > MAX_CHANGESET_FRACTION:
        raise PublishError("LARGE_CHANGESET")
    say("REMOTE HEAD: " + head)
    say("REMOTE TREE: " + tree_sha)
    say("ADDED: " + str(len(added)))
    for rel in added: say("  + " + rel)
    say("MODIFIED: " + str(len(modified)))
    for rel in modified: say("  ~ " + rel)
    say("DELETED: " + str(len(deleted)))
    for rel in deleted: say("  - " + rel)
    say("UNCHANGED: " + str(len(unchanged)))
    say("PAYLOAD SIZE: " + str(total) + " bytes")
    say("SECRET_SCAN: PASS")
    say("PAYLOAD_SCAN: PASS")
    say("RATE LIMIT: " + str(remaining) + "/" + str(limit))
    if approval:
        say("ONE_TIME_MANIFEST: MATCH")
    return {"head": head, "state": state, "tree_sha": tree_sha, "remote_blobs": remote_blobs,
            "local": local, "local_hash": local_hash, "added": added, "modified": modified,
            "deleted": deleted, "unchanged": unchanged, "payload_size": total,
            "rate_remaining": remaining, "rate_limit": limit, "remote_files": remote_files,
            "one_time_manifest": approval}


def create_blob(path, data, token):
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise PublishError("API_FAILED", "local file is not UTF-8")
    _, result, _ = request("POST", f"/repos/{OWNER}/{REPO}/git/blobs", token,
                           {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"})
    sha = result.get("sha")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise PublishError("API_FAILED", "blob response did not contain a SHA")
    return sha


def publish(message, token, diff):
    if not token:
        raise PublishError("WAITING_FOR_GITHUB_TOKEN")
    changed_blobs = len(diff["added"]) + len(diff["modified"])
    needed = changed_blobs + 10
    fresh_remaining, _ = get_rate(token)
    if fresh_remaining < max(MIN_RATE_REMAINING, needed):
        raise PublishError("RATE_LIMIT_LOW")
    description = message.strip()
    if description.startswith("arcade:"):
        description = description[len("arcade:"):].strip()
    if not description or any(ord(c) < 32 for c in description):
        raise PublishError("API_FAILED", "invalid commit description")
    commit_message = "arcade: " + description
    tree_entries = []
    for rel in diff["added"] + diff["modified"]:
        blob_sha = create_blob(rel, diff["local"][rel], token)
        tree_entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob_sha})
    for rel in diff["deleted"]:
        tree_entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": None})
    if not tree_entries:
        say("NO_CHANGES")
        return None
    _, created_tree, _ = request("POST", f"/repos/{OWNER}/{REPO}/git/trees", token,
                                 {"base_tree": diff["tree_sha"], "tree": tree_entries})
    new_tree = created_tree.get("sha")
    if not isinstance(new_tree, str):
        raise PublishError("API_FAILED", "tree response did not contain a SHA")
    _, created_commit, _ = request("POST", f"/repos/{OWNER}/{REPO}/git/commits", token,
                                   {"message": commit_message, "tree": new_tree,
                                    "parents": [diff["head"]]})
    new_commit = created_commit.get("sha")
    if not isinstance(new_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", new_commit):
        raise PublishError("API_FAILED", "commit response did not contain a SHA")
    current = get_head(token)
    if current != diff["head"]:
        raise PublishError("REMOTE_CHANGED_DURING_PUBLISH", "main changed after commit object creation")
    # One non-force ref update. Never retry this write; verify the ref after any ambiguous response.
    try:
        _, updated, _ = request("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", token,
                                {"sha": new_commit, "force": False}, retries=1)
    except PublishError as e:
        try:
            observed_head = get_head(token)
            if observed_head == new_commit:
                updated = {"object": {"sha": new_commit}}
            elif observed_head != diff["head"]:
                raise PublishError("REMOTE_CHANGED_DURING_PUBLISH", "main changed during ref update")
            else:
                raise e
        except PublishError as check_error:
            if check_error.category == "REMOTE_CHANGED_DURING_PUBLISH":
                raise
            raise e
    if updated.get("object", {}).get("sha") != new_commit:
        raise PublishError("API_FAILED", "ref update response did not match the new commit")
    final_head = get_head(token)
    if final_head != new_commit:
        raise PublishError("API_FAILED", "main did not advance to the requested commit")
    _, verified, _ = request("GET", f"/repos/{OWNER}/{REPO}/git/commits/{new_commit}", token)
    if (verified.get("message") != commit_message or verified.get("tree", {}).get("sha") != new_tree
            or verified.get("parents", [{}])[0].get("sha") != diff["head"]):
        raise PublishError("API_FAILED", "post-publish commit verification failed")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    state = {"repository": OWNER + "/" + REPO, "branch": BRANCH,
             "last_known_remote_sha": new_commit, "last_successful_publish_sha": new_commit,
             "last_publish_at": now}
    atomic_json(STATE_FILE, state)
    say("PUBLISH_PASS")
    say("COMMIT SHA: " + new_commit)
    say("BRANCH: " + BRANCH)
    say("REMOTE: " + OWNER + "/" + REPO)
    say("STATUS: CLEAN_REMOTE_HEAD_VERIFIED")
    return new_commit


def main():
    parser = argparse.ArgumentParser(description="Publish the filtered arcade audit to its fixed GitHub repository.")
    parser.add_argument("--message", required=False)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--one-time-approved", action="store_true",
                        help="use only the fixed, exact-file one-time approval manifest")
    parser.add_argument("--scope", choices=sorted(EXPORT_SCOPES), default="all",
                        help="limit export synchronization to an explicit reviewed file scope")
    parser.add_argument("--sync-export", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--allow-publish", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.sync_export:
            result = sync_export(args.scope)
            say("EXPORT_SYNC_PASS")
            say("EXPORT_SCOPE: " + result["scope"])
            say("ADDED: " + str(len(result["added"])))
            for p in result["added"]: say("  + " + p)
            say("MODIFIED: " + str(len(result["modified"])))
            for p in result["modified"]: say("  ~ " + p)
            say("DELETED: " + str(len(result["deleted"])))
            for p in result["deleted"]: say("  - " + p)
            say("UNCHANGED: " + str(result["unchanged"]))
            return 0
        if not args.message:
            raise PublishError("API_FAILED", "--message is required")
        if not EXPORT.is_dir():
            raise PublishError("EXPORT_SYNC_FAIL", "export directory missing")
        files = export_files()
        credential_value = load_token(required=not args.dry_run)
        secret_scan(files, credential_value)
        payload_size = payload_scan(files)
        say("SECRET_SCAN: PASS")
        say("PAYLOAD_SCAN: PASS")
        say("PAYLOAD SIZE: " + str(payload_size) + " bytes")
        diff = scan_and_diff(credential_value, one_time_approved=args.one_time_approved)
        if args.dry_run:
            if not (diff["added"] or diff["modified"] or diff["deleted"]):
                say("NO_CHANGES")
            say("DRY_RUN_PASS")
            return 0
        if not args.allow_publish:
            raise PublishError("API_FAILED", "direct publish requires the wrapper authorization flag")
        if diff.get("one_time_manifest"):
            consume_one_time_manifest(diff["one_time_manifest"])
        publish(args.message, credential_value, diff)
        return 0
    except PublishError as e:
        say(e.category)
        if e.detail:
            say("DETAIL: " + e.detail)
        return 3 if e.category == "WAITING_FOR_GITHUB_TOKEN" else 1
    except KeyboardInterrupt:
        say("UNKNOWN")
        return 130
    except Exception as exc:
        # Keep diagnostics useful without exposing request details or credentials.
        say("ERROR_TYPE: " + type(exc).__name__)
        if isinstance(exc, NameError):
            say("ERROR_NAME: " + str(exc.name))
        say("UNKNOWN")
        return 1


if __name__ == "__main__":
    sys.exit(main())
