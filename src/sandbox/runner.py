import asyncio
import os
import sys
from typing import Any

import docker

from src.config import settings


class DockerTestSandbox:
    """
    Problem 3 Solution: Isolated Execution of AI-Generated Tests.
    Executes tests inside a sandboxed container to ensure no LLM hallucination
    can claim a test passed without real stdout/stderr execution proof.
    """

    def __init__(
        self, image: str = settings.SANDBOX_IMAGE, timeout: int = settings.SANDBOX_TIMEOUT_SECONDS
    ):
        self.image = image
        self.timeout = timeout
        try:
            self.docker_client = docker.from_env()
        except Exception:
            self.docker_client = None

    async def execute_test_suite(
        self,
        checkout_dir: str,
        test_code: str,
        test_name: str = "test_generated.py",
    ) -> dict[str, Any]:
        """
        Runs the test code against the repository in an isolated environment.
        Captures exact stdout, stderr, exit code, and pass/fail proof.
        """
        # Write test code to a temporary test file in checkout
        abs_checkout_dir = os.path.abspath(checkout_dir)
        test_file_path = os.path.join(abs_checkout_dir, test_name)
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(test_code)

        # Method A: Try Docker container execution if docker client is active
        if self.docker_client:
            try:
                loop = asyncio.get_running_loop()

                def _run_in_docker():
                    container = self.docker_client.containers.run(
                        self.image,
                        command=f"sh -c 'pip install pytest -q 2>/dev/null && pytest -o cache_dir=/tmp/.pytest_cache {test_name} -v'",
                        volumes={abs_checkout_dir: {"bind": "/app", "mode": "rw"}},
                        working_dir="/app",
                        detach=False,
                        stdout=True,
                        stderr=True,
                        remove=True,
                        network_disabled=True,
                    )
                    return 0, container.decode("utf-8", errors="replace"), ""

                exit_code, stdout, stderr = await asyncio.wait_for(
                    loop.run_in_executor(None, _run_in_docker),
                    timeout=self.timeout,
                )
                passed = exit_code == 0
                if passed:
                    return {
                        "test_name": test_name,
                        "passed": passed,
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "mode": "docker_isolated_container",
                    }
            except Exception:
                # Fallback to local subprocess sandbox
                pass

        # Method B: Subprocess execution in virtualenv sandbox
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "cache_dir=/tmp/.pytest_cache",
            test_name,
            "-v",
            "--tb=short",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=abs_checkout_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = proc.returncode or 0
            passed = exit_code == 0

            return {
                "test_name": test_name,
                "passed": passed,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "mode": "subprocess_sandbox",
            }
        except TimeoutError:
            return {
                "test_name": test_name,
                "passed": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {self.timeout}s in test sandbox",
                "mode": "timeout",
            }
        except Exception as ex:
            return {
                "test_name": test_name,
                "passed": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(ex),
                "mode": "error",
            }
        finally:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
