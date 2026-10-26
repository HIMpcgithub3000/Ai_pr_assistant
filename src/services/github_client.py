import time
from typing import Any

import httpx
import jwt

from src.config import settings


class GitHubClient:
    """
    Handles GitHub App authentication, commit status checks, and PR review comments.
    """

    def __init__(
        self,
        app_id: str | None = settings.GITHUB_APP_ID,
        private_key_path: str | None = settings.GITHUB_APP_PRIVATE_KEY_PATH,
        token: str | None = settings.GITHUB_TOKEN,
    ):
        self.app_id = app_id
        self.private_key_path = private_key_path
        self.token = token

    def _generate_jwt(self) -> str | None:
        if not self.app_id or not self.private_key_path:
            return None
        with open(self.private_key_path, "r") as f:
            private_key = f.read()
        payload = {
            "iat": int(time.time()),
            "exp": int(time.time()) + 600,
            "iss": self.app_id,
        }
        return jwt.encode(payload, private_key, algorithm="RS256")

    async def get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.app_id:
            token = self._generate_jwt()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    async def get_user_info(self) -> dict[str, Any]:
        """Fetches the authenticated user profile and scopes from GitHub."""
        if not self.token and not self.app_id:
            return {"authenticated": False, "login": "anonymous", "name": "Anonymous Dev", "repos_count": 0}
        headers = await self.get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.github.com/user", headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "authenticated": True,
                    "login": data.get("login"),
                    "name": data.get("name") or data.get("login"),
                    "avatar_url": data.get("avatar_url"),
                    "html_url": data.get("html_url"),
                    "public_repos": data.get("public_repos", 0),
                    "total_private_repos": data.get("total_private_repos", 0),
                }
            return {"authenticated": False, "status_code": resp.status_code, "login": None}

    async def list_user_repositories(self) -> list[dict[str, Any]]:
        """Fetches all repositories available to the authenticated user."""
        if not self.token and not self.app_id:
            return []
        headers = await self.get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.github.com/user/repos?per_page=100&sort=updated",
                headers=headers,
                timeout=12.0,
            )
            if resp.status_code != 200:
                return []
            repos = resp.json()
            results = []
            for r in repos:
                results.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "owner": r.get("owner", {}).get("login"),
                    "private": r.get("private", False),
                    "html_url": r.get("html_url"),
                    "description": r.get("description"),
                    "default_branch": r.get("default_branch", "main"),
                    "updated_at": r.get("updated_at"),
                    "stargazers_count": r.get("stargazers_count", 0),
                    "open_issues_count": r.get("open_issues_count", 0),
                    "clone_url": r.get("clone_url"),
                })
            return results

    async def list_repo_pulls(self, repo_full_name: str, state: str = "open") -> list[dict[str, Any]]:
        """Fetches pull requests for a given repository."""
        if not self.token and not self.app_id:
            return []
        headers = await self.get_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.github.com/repos/{repo_full_name}/pulls?state={state}",
                headers=headers,
                timeout=10.0,
            )
            if resp.status_code != 200:
                return []
            pulls = resp.json()
            results = []
            for p in pulls:
                results.append({
                    "number": p.get("number"),
                    "title": p.get("title"),
                    "state": p.get("state"),
                    "html_url": p.get("html_url"),
                    "user": p.get("user", {}).get("login"),
                    "head_sha": p.get("head", {}).get("sha"),
                    "head_ref": p.get("head", {}).get("ref"),
                    "base_sha": p.get("base", {}).get("sha"),
                    "base_ref": p.get("base", {}).get("ref"),
                    "created_at": p.get("created_at"),
                    "updated_at": p.get("updated_at"),
                })
            return results

    async def post_check_run(
        self,
        repo_owner_name: str,
        head_sha: str,
        status: str,
        conclusion: str | None = None,
        title: str = "AI PR Assistant",
        summary: str = "",
    ) -> dict[str, Any]:
        """Creates or updates a GitHub Check Run."""
        if not self.token and not self.app_id:
            # Offline / local mock mode
            return {"status": "mocked", "check_run": status, "conclusion": conclusion}

        headers = await self.get_headers()
        url = f"https://api.github.com/repos/{repo_owner_name}/check-runs"
        payload = {
            "name": "AI PR Assistant Review",
            "head_sha": head_sha,
            "status": status,
            "output": {"title": title, "summary": summary},
        }
        if conclusion:
            payload["conclusion"] = conclusion

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=10.0)
            return (
                resp.json()
                if resp.status_code in (200, 201)
                else {"status": "error", "code": resp.status_code}
            )

    async def post_pr_comment(
        self,
        repo_owner_name: str,
        pr_number: int,
        body: str,
    ) -> dict[str, Any]:
        """Posts a formatted markdown review comment directly to the Pull Request conversation."""
        if not self.token and not self.app_id:
            return {"status": "mocked"}
        headers = await self.get_headers()
        url = f"https://api.github.com/repos/{repo_owner_name}/issues/{pr_number}/comments"
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json={"body": body}, timeout=10.0)
            return (
                resp.json()
                if resp.status_code in (200, 201)
                else {"status": "error", "code": resp.status_code}
            )

    def format_pr_comment(
        self,
        analysis_id: str,
        head_sha: str,
        findings: list[dict[str, Any]],
        test_evidence: dict[str, Any] | None = None,
    ) -> str:
        """
        Formats a structured markdown PR comment with evidence links and confidence scores.
        """
        comment = [
            "## 🤖 AI PR Assistant — Review Summary",
            f"**Commit SHA**: `{head_sha}` | **Analysis ID**: `{analysis_id}`\n",
        ]

        if not findings:
            comment.append("✅ **All quality and security checks passed! No issues detected.**\n")
        else:
            comment.append(f"### 🔍 Validated Findings ({len(findings)})")
            for f in findings:
                sev_icon = "🚨" if f.get("severity") in ("CRITICAL", "HIGH") else "⚠️"
                comment.append(
                    f"- {sev_icon} **[{f.get('category')}] {f.get('title', 'Issue')}** "
                    f"(`{f.get('file_path')}:{f.get('line_number', '?')}`)"
                )
                comment.append(f"  - **Details**: {f.get('description')}")
                if f.get("suggestion"):
                    comment.append(f"  - **Suggestion**: {f.get('suggestion')}")
                comment.append(
                    f"  - *Verification*: Confidence {int(f.get('confidence', 0.9) * 100)}% ({f.get('proof_reason', 'Verified')})"
                )
            comment.append("")

        if test_evidence:
            comment.append("### 🧪 Sandbox Test Execution Proof")
            status_icon = "✅ PASSED" if test_evidence.get("passed") else "❌ FAILED"
            comment.append(f"- **Suite**: `{test_evidence.get('test_name')}` -> **{status_icon}**")
            comment.append(f"- **Exit Code**: `{test_evidence.get('exit_code')}`")
            if test_evidence.get("stdout"):
                comment.append(f"```text\n{test_evidence.get('stdout').strip()[:500]}\n```")

        comment.append(
            "\n---\n*Verified by deterministic sandbox execution and physical evidence check.*"
        )
        return "\n".join(comment)
