import asyncio
import os
import shutil

from src.config import settings


class GitManager:
    """
    Solves Bottleneck #1: Shared Clone Cache Layer.
    Instead of doing a full clone per PR sandbox, maintains a shared bare repository cache
    and fetches only the target commits, checking out exact HEAD_SHA and BASE_SHA.
    """

    def __init__(self, cache_dir: str = settings.GIT_CACHE_DIR):
        self.cache_dir = os.path.abspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_repo_cache_path(self, repo_id: str) -> str:
        # e.g., cache/git/org_repo
        safe_name = repo_id.replace("/", "_").replace(":", "_")
        return os.path.join(self.cache_dir, safe_name)

    async def _run_command(self, cmd: list[str], cwd: str) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return (
            proc.returncode,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    def _format_authenticated_url(self, clone_url: str) -> str:
        if settings.GITHUB_TOKEN and "github.com/" in clone_url and "@" not in clone_url:
            return clone_url.replace("https://github.com/", f"https://x-access-token:{settings.GITHUB_TOKEN}@github.com/")
        return clone_url

    async def ensure_cached_repo(self, repo_id: str, clone_url: str) -> str:
        repo_path = self._get_repo_cache_path(repo_id)
        auth_url = self._format_authenticated_url(clone_url)
        if not os.path.exists(repo_path):
            # Create a mirror/bare cache or initial clone
            os.makedirs(repo_path, exist_ok=True)
            cmd = ["git", "clone", "--bare", auth_url, repo_path]
            code, _out, err = await self._run_command(cmd, cwd=self.cache_dir)
            if code != 0:
                # If local or mock repo URL
                if os.path.isdir(clone_url):
                    cmd = ["git", "clone", "--bare", clone_url, repo_path]
                    code, _out, err = await self._run_command(cmd, cwd=self.cache_dir)
                if code != 0:
                    raise RuntimeError(f"Failed to initialize repo cache for {repo_id}: {err}")
        return repo_path

    async def checkout_exact_sha(
        self,
        repo_id: str,
        clone_url: str,
        head_sha: str,
        base_sha: str,
        target_dir: str,
    ) -> dict[str, str]:
        """
        Creates an isolated analysis checkout locked strictly to head_sha and base_sha.
        Generates deterministic diff between base_sha and head_sha.
        """
        target_dir = os.path.abspath(target_dir)
        os.makedirs(target_dir, exist_ok=True)
        repo_cache = await self.ensure_cached_repo(repo_id, clone_url)

        # Fetch head_sha and base_sha explicitly into cache with named refs
        auth_url = self._format_authenticated_url(clone_url)
        await self._run_command(["git", "fetch", auth_url, f"+{head_sha}:refs/commits/{head_sha}"], cwd=repo_cache)
        await self._run_command(["git", "fetch", auth_url, f"+{base_sha}:refs/commits/{base_sha}"], cwd=repo_cache)

        # Clone from local cache into target checkout directory
        clone_cmd = ["git", "clone", repo_cache, target_dir]
        code, _, err = await self._run_command(clone_cmd, cwd=self.cache_dir)
        if code != 0:
            raise RuntimeError(f"Failed to clone from cache: {err}")

        # Fetch the refs from local cache into target_dir
        await self._run_command(["git", "fetch", "origin", f"refs/commits/{head_sha}:refs/commits/{head_sha}"], cwd=target_dir)
        await self._run_command(["git", "fetch", "origin", f"refs/commits/{base_sha}:refs/commits/{base_sha}"], cwd=target_dir)

        # Checkout exact HEAD SHA
        checkout_cmd = ["git", "checkout", head_sha]
        code, _, err = await self._run_command(checkout_cmd, cwd=target_dir)
        if code != 0:
            raise RuntimeError(f"Failed to checkout {head_sha}: {err}")

        # Compute deterministic diff against BASE_SHA
        diff_cmd = ["git", "diff", f"{base_sha}..{head_sha}"]
        _, diff_output, _ = await self._run_command(diff_cmd, cwd=target_dir)

        # Get changed file list
        files_cmd = ["git", "diff", "--name-only", f"{base_sha}..{head_sha}"]
        _, files_output, _ = await self._run_command(files_cmd, cwd=target_dir)
        changed_files = [f.strip() for f in files_output.splitlines() if f.strip()]

        return {
            "checkout_dir": target_dir,
            "head_sha": head_sha,
            "base_sha": base_sha,
            "diff": diff_output,
            "changed_files": changed_files,
        }

    async def cleanup_checkout(self, target_dir: str) -> None:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
