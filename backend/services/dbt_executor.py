"""
dbt Execution Service.

Handles the actual execution of dbt commands including:
- Git repository cloning and management
- dbt environment setup and profiles.yml generation
- Command execution with timeout and log capture
- Artifact parsing (run_results.json, manifest.json)

Security notes:
- Git credentials are passed via environment variables, never embedded in URLs
- All error messages are sanitized to prevent credential leakage
- Execution timeout is enforced (max 30 minutes)
"""
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib

logger = logging.getLogger(__name__)

# Maximum execution timeout (30 minutes)
MAX_EXECUTION_TIMEOUT_SECONDS = 1800

# Git clone timeout (2 minutes)
GIT_CLONE_TIMEOUT_SECONDS = 120

# dbt deps install timeout (5 minutes)
DBT_DEPS_TIMEOUT_SECONDS = 300


@dataclass
class DbtExecutionConfig:
    """Configuration for a dbt execution."""
    # Git configuration
    git_repo_url: str
    git_branch: str = "main"
    git_subdirectory: Optional[str] = None
    git_credentials: Optional[Dict[str, Any]] = None

    # dbt configuration
    command: str = "run"
    target: str = "prod"
    select: Optional[str] = None
    exclude: Optional[str] = None
    full_refresh: bool = False
    dbt_version: Optional[str] = None

    # Environment and profiles
    profiles_yml: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None

    # Execution settings
    timeout_seconds: int = MAX_EXECUTION_TIMEOUT_SECONDS


@dataclass
class DbtExecutionResult:
    """Result of a dbt execution."""
    success: bool
    logs: str = ""
    error_message: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Model/test statistics
    models_ran: int = 0
    models_passed: int = 0
    models_failed: int = 0
    models_skipped: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_warned: int = 0

    # Artifacts
    run_results_json: Optional[Dict[str, Any]] = None
    manifest_json: Optional[Dict[str, Any]] = None


class CredentialSanitizer:
    """Utility to sanitize credentials from log output and error messages."""

    def __init__(self, credentials: Optional[Dict[str, Any]] = None):
        self.sensitive_values: List[str] = []
        if credentials:
            if credentials.get('token'):
                self.sensitive_values.append(credentials['token'])
            if credentials.get('password'):
                self.sensitive_values.append(credentials['password'])
            if credentials.get('ssh_key'):
                self.sensitive_values.append(credentials['ssh_key'])
            if credentials.get('username'):
                # Username is less sensitive but still worth masking in URLs
                self.sensitive_values.append(credentials['username'])

        # Also check environment variables
        for key in ['GIT_PASSWORD', 'GIT_TOKEN', 'GIT_USERNAME']:
            val = os.environ.get(key)
            if val:
                self.sensitive_values.append(val)

    def sanitize(self, text: str) -> str:
        """Remove sensitive values from text."""
        result = text
        for sensitive in self.sensitive_values:
            if sensitive and len(sensitive) > 0:
                result = result.replace(sensitive, '[REDACTED]')

        # Also redact any URLs with embedded credentials
        # Pattern: https://user:pass@host or https://token@host
        result = re.sub(
            r'(https?://)[^:@\s]+:[^@\s]+@',
            r'\1[REDACTED]:[REDACTED]@',
            result
        )
        result = re.sub(
            r'(https?://)[^@\s]+@',
            r'\1[REDACTED]@',
            result
        )

        return result


class GitManager:
    """Manages git repository operations."""

    def __init__(
        self,
        repo_url: str,
        branch: str = "main",
        credentials: Optional[Dict[str, Any]] = None,
        subdirectory: Optional[str] = None,
    ):
        self.repo_url = repo_url
        self.branch = branch
        self.credentials = credentials or {}
        self.subdirectory = subdirectory
        self.sanitizer = CredentialSanitizer(credentials)
        self._temp_dir: Optional[str] = None
        self._ssh_key_file: Optional[str] = None

    def _get_cache_key(self) -> str:
        """Generate a cache key for this repository."""
        key_data = f"{self.repo_url}:{self.branch}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _build_git_env(self) -> Dict[str, str]:
        """Build environment variables for git operations."""
        env = os.environ.copy()
        env['GIT_TERMINAL_PROMPT'] = '0'  # Disable interactive prompts

        # Use credentials from environment variables if available (preferred)
        git_username = os.environ.get('GIT_USERNAME')
        git_password = os.environ.get('GIT_PASSWORD')

        # Fall back to project-level credentials
        if not git_username and self.credentials.get('username'):
            git_username = self.credentials['username']
        if not git_password and self.credentials.get('token'):
            git_password = self.credentials['token']

        if git_username and git_password and self.repo_url.startswith('https://'):
            # Use credential helper via environment
            env['GIT_USERNAME'] = git_username
            env['GIT_PASSWORD'] = git_password
            # Configure git to use credential from environment
            env['GIT_CONFIG_COUNT'] = '1'
            env['GIT_CONFIG_KEY_0'] = 'credential.helper'
            env['GIT_CONFIG_VALUE_0'] = '!f() { echo "username=$GIT_USERNAME"; echo "password=$GIT_PASSWORD"; }; f'

        return env

    def _setup_ssh_key(self, env: Dict[str, str]) -> None:
        """Set up SSH key for git operations."""
        ssh_key = self.credentials.get('ssh_key')
        if not ssh_key:
            return

        # Write SSH key to a temporary file
        import tempfile
        fd, self._ssh_key_file = tempfile.mkstemp(prefix='dbt_ssh_', suffix='.key')
        os.write(fd, ssh_key.encode())
        os.close(fd)
        os.chmod(self._ssh_key_file, 0o600)

        # Configure SSH to use this key
        env['GIT_SSH_COMMAND'] = f'ssh -i {self._ssh_key_file} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

    def _cleanup_ssh_key(self) -> None:
        """Clean up temporary SSH key file."""
        if self._ssh_key_file and os.path.exists(self._ssh_key_file):
            try:
                os.remove(self._ssh_key_file)
            except Exception:
                pass
            self._ssh_key_file = None

    def clone(self, target_dir: str) -> Tuple[bool, str]:
        """
        Clone the repository to target directory.

        Returns:
            Tuple of (success, message/error)
        """
        env = self._build_git_env()

        try:
            # Set up SSH key if provided
            if self.repo_url.startswith('git@'):
                self._setup_ssh_key(env)

            # Clone with depth 1 for faster cloning
            result = subprocess.run(
                [
                    'git', 'clone',
                    '--depth', '1',
                    '--branch', self.branch,
                    '--single-branch',
                    self.repo_url,
                    target_dir,
                ],
                capture_output=True,
                text=True,
                timeout=GIT_CLONE_TIMEOUT_SECONDS,
                env=env,
            )

            if result.returncode != 0:
                error_msg = self.sanitizer.sanitize(result.stderr.strip())
                return False, f"Git clone failed: {error_msg}"

            return True, "Repository cloned successfully"

        except subprocess.TimeoutExpired:
            return False, "Git clone timed out"
        except Exception as e:
            error_msg = self.sanitizer.sanitize(str(e))
            return False, f"Git clone error: {error_msg}"
        finally:
            self._cleanup_ssh_key()

    def pull(self, repo_dir: str) -> Tuple[bool, str]:
        """
        Pull latest changes for an existing repository.

        Returns:
            Tuple of (success, message/error)
        """
        env = self._build_git_env()

        try:
            if self.repo_url.startswith('git@'):
                self._setup_ssh_key(env)

            # Fetch and reset to origin
            result = subprocess.run(
                ['git', 'fetch', '--depth', '1', 'origin', self.branch],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=GIT_CLONE_TIMEOUT_SECONDS,
                env=env,
            )

            if result.returncode != 0:
                error_msg = self.sanitizer.sanitize(result.stderr.strip())
                return False, f"Git fetch failed: {error_msg}"

            # Reset to origin branch
            result = subprocess.run(
                ['git', 'reset', '--hard', f'origin/{self.branch}'],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )

            if result.returncode != 0:
                error_msg = self.sanitizer.sanitize(result.stderr.strip())
                return False, f"Git reset failed: {error_msg}"

            return True, "Repository updated successfully"

        except subprocess.TimeoutExpired:
            return False, "Git pull timed out"
        except Exception as e:
            error_msg = self.sanitizer.sanitize(str(e))
            return False, f"Git pull error: {error_msg}"
        finally:
            self._cleanup_ssh_key()

    def get_project_directory(self, base_dir: str) -> str:
        """Get the dbt project directory within the cloned repo."""
        if self.subdirectory:
            return os.path.join(base_dir, self.subdirectory)
        return base_dir


class DbtProfileGenerator:
    """Generates profiles.yml for dbt execution."""

    @staticmethod
    def generate(
        target: str,
        profiles_yml: Optional[str] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate or validate profiles.yml content.

        If profiles_yml is provided, use it directly (with env var substitution).
        Otherwise, generate a minimal profile that relies on environment variables.
        """
        if profiles_yml:
            return profiles_yml

        # Generate a minimal profile that uses environment variables
        # Users should provide their own profiles.yml or set env vars
        profile = f"""
# Auto-generated dbt profile
# Configure via environment variables or provide custom profiles.yml
default:
  target: {target}
  outputs:
    {target}:
      type: "{{{{ env_var('DBT_TYPE', 'postgres') }}}}"
      host: "{{{{ env_var('DBT_HOST', 'localhost') }}}}"
      port: "{{{{ env_var('DBT_PORT', '5432') | int }}}}"
      user: "{{{{ env_var('DBT_USER', 'postgres') }}}}"
      password: "{{{{ env_var('DBT_PASSWORD', '') }}}}"
      dbname: "{{{{ env_var('DBT_DATABASE', 'analytics') }}}}"
      schema: "{{{{ env_var('DBT_SCHEMA', 'public') }}}}"
      threads: "{{{{ env_var('DBT_THREADS', '4') | int }}}}"
"""
        return profile


class DbtCommandBuilder:
    """Builds dbt command arguments."""

    SUPPORTED_COMMANDS = [
        'run', 'test', 'build', 'compile', 'seed',
        'snapshot', 'docs', 'source', 'debug', 'deps'
    ]

    @classmethod
    def build(
        cls,
        command: str,
        target: Optional[str] = None,
        select: Optional[str] = None,
        exclude: Optional[str] = None,
        full_refresh: bool = False,
    ) -> List[str]:
        """
        Build dbt command arguments.

        Returns:
            List of command arguments (without 'dbt' prefix)
        """
        if command not in cls.SUPPORTED_COMMANDS:
            raise ValueError(f"Unsupported dbt command: {command}")

        args = [command]

        # Add target
        if target:
            args.extend(['--target', target])

        # Add selection
        if select:
            args.extend(['--select', select])

        # Add exclusion
        if exclude:
            args.extend(['--exclude', exclude])

        # Add full-refresh (only for relevant commands)
        if full_refresh and command in ('run', 'build', 'seed'):
            args.append('--full-refresh')

        # Add profiles-dir to use our generated profile
        args.extend(['--profiles-dir', '.'])

        return args


class ArtifactParser:
    """Parses dbt artifacts (run_results.json, manifest.json)."""

    @staticmethod
    def parse_run_results(target_dir: str) -> Optional[Dict[str, Any]]:
        """Parse target/run_results.json."""
        results_path = os.path.join(target_dir, 'target', 'run_results.json')
        if not os.path.exists(results_path):
            return None

        try:
            with open(results_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to parse run_results.json: {e}")
            return None

    @staticmethod
    def parse_manifest(target_dir: str) -> Optional[Dict[str, Any]]:
        """Parse target/manifest.json."""
        manifest_path = os.path.join(target_dir, 'target', 'manifest.json')
        if not os.path.exists(manifest_path):
            return None

        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to parse manifest.json: {e}")
            return None

    @staticmethod
    def extract_stats(run_results: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract model and test statistics from run_results.

        Returns dict with keys:
        - models_ran, models_passed, models_failed, models_skipped
        - tests_passed, tests_failed, tests_warned
        """
        stats = {
            'models_ran': 0,
            'models_passed': 0,
            'models_failed': 0,
            'models_skipped': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_warned': 0,
        }

        results = run_results.get('results', [])

        for result in results:
            node_type = result.get('unique_id', '').split('.')[0]
            status = result.get('status', '')

            if node_type == 'model':
                stats['models_ran'] += 1
                if status == 'success':
                    stats['models_passed'] += 1
                elif status == 'error':
                    stats['models_failed'] += 1
                elif status == 'skipped':
                    stats['models_skipped'] += 1

            elif node_type == 'test':
                if status == 'pass':
                    stats['tests_passed'] += 1
                elif status == 'fail':
                    stats['tests_failed'] += 1
                elif status == 'warn':
                    stats['tests_warned'] += 1

            # Also count seeds and snapshots as models for simplicity
            elif node_type in ('seed', 'snapshot'):
                stats['models_ran'] += 1
                if status == 'success':
                    stats['models_passed'] += 1
                elif status == 'error':
                    stats['models_failed'] += 1
                elif status == 'skipped':
                    stats['models_skipped'] += 1

        return stats


class DbtExecutor:
    """
    Main dbt execution engine.

    Handles the full lifecycle of a dbt run:
    1. Clone/pull git repository
    2. Set up dbt environment (profiles.yml, env vars)
    3. Install dbt dependencies
    4. Execute dbt command
    5. Parse results and artifacts
    6. Clean up
    """

    def __init__(self, config: DbtExecutionConfig):
        self.config = config
        self.sanitizer = CredentialSanitizer(config.git_credentials)
        self._temp_dir: Optional[str] = None
        self._logs: List[str] = []

    def _log(self, message: str) -> None:
        """Add a log entry."""
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        self._logs.append(f"[{timestamp}] {message}")
        logger.info(message)

    def _get_logs(self) -> str:
        """Get all logs as a single string."""
        return '\n'.join(self._logs)

    def _setup_temp_directory(self) -> str:
        """Create a temporary directory for the dbt project."""
        self._temp_dir = tempfile.mkdtemp(prefix='dbt_run_')
        self._log(f"Created temporary directory: {self._temp_dir}")
        return self._temp_dir

    def _cleanup(self) -> None:
        """Clean up temporary files."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                self._log(f"Cleaned up temporary directory")
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir: {e}")

    def _build_env(self) -> Dict[str, str]:
        """Build environment variables for dbt execution."""
        env = os.environ.copy()

        # Add project-level env vars
        if self.config.env_vars:
            for key, value in self.config.env_vars.items():
                env[key] = value

        # Set HOME to temp dir to avoid polluting user home
        if self._temp_dir:
            env['DBT_PROFILES_DIR'] = self._temp_dir

        return env

    def _write_profiles_yml(self, project_dir: str) -> None:
        """Write profiles.yml to the project directory."""
        profiles_content = DbtProfileGenerator.generate(
            target=self.config.target,
            profiles_yml=self.config.profiles_yml,
            env_vars=self.config.env_vars,
        )

        profiles_path = os.path.join(project_dir, 'profiles.yml')
        with open(profiles_path, 'w') as f:
            f.write(profiles_content)

        self._log("Generated profiles.yml")

    def _run_dbt_deps(self, project_dir: str, env: Dict[str, str]) -> Tuple[bool, str]:
        """Run dbt deps to install packages."""
        self._log("Installing dbt dependencies...")

        try:
            result = subprocess.run(
                ['dbt', 'deps', '--profiles-dir', '.'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=DBT_DEPS_TIMEOUT_SECONDS,
                env=env,
            )

            output = result.stdout + result.stderr
            self._logs.append(self.sanitizer.sanitize(output))

            if result.returncode != 0:
                return False, self.sanitizer.sanitize(result.stderr)

            self._log("dbt dependencies installed successfully")
            return True, ""

        except subprocess.TimeoutExpired:
            return False, "dbt deps timed out"
        except FileNotFoundError:
            return False, "dbt command not found. Ensure dbt is installed."
        except Exception as e:
            return False, self.sanitizer.sanitize(str(e))

    def _run_dbt_command(
        self,
        project_dir: str,
        env: Dict[str, str],
    ) -> Tuple[bool, str, str]:
        """
        Execute the dbt command.

        Returns:
            Tuple of (success, stdout, stderr)
        """
        args = DbtCommandBuilder.build(
            command=self.config.command,
            target=self.config.target,
            select=self.config.select,
            exclude=self.config.exclude,
            full_refresh=self.config.full_refresh,
        )

        full_command = ['dbt'] + args
        self._log(f"Executing: dbt {' '.join(args)}")

        try:
            result = subprocess.run(
                full_command,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                env=env,
            )

            return (
                result.returncode == 0,
                self.sanitizer.sanitize(result.stdout),
                self.sanitizer.sanitize(result.stderr),
            )

        except subprocess.TimeoutExpired:
            return False, "", f"dbt command timed out after {self.config.timeout_seconds} seconds"
        except FileNotFoundError:
            return False, "", "dbt command not found. Ensure dbt is installed."
        except Exception as e:
            return False, "", self.sanitizer.sanitize(str(e))

    def execute(self) -> DbtExecutionResult:
        """
        Execute the full dbt run.

        Returns:
            DbtExecutionResult with execution details and artifacts
        """
        result = DbtExecutionResult(success=False)
        result.started_at = datetime.now(timezone.utc)

        try:
            # Step 1: Set up temp directory
            temp_dir = self._setup_temp_directory()

            # Step 2: Clone repository
            self._log(f"Cloning repository: {self.config.git_repo_url} (branch: {self.config.git_branch})")

            git_manager = GitManager(
                repo_url=self.config.git_repo_url,
                branch=self.config.git_branch,
                credentials=self.config.git_credentials,
                subdirectory=self.config.git_subdirectory,
            )

            success, message = git_manager.clone(temp_dir)
            self._log(message)

            if not success:
                result.error_message = message
                return result

            # Step 3: Get project directory
            project_dir = git_manager.get_project_directory(temp_dir)

            if not os.path.exists(os.path.join(project_dir, 'dbt_project.yml')):
                result.error_message = f"dbt_project.yml not found in {self.config.git_subdirectory or 'repository root'}"
                return result

            self._log(f"dbt project found at: {project_dir}")

            # Step 4: Write profiles.yml
            self._write_profiles_yml(project_dir)

            # Step 5: Build environment
            env = self._build_env()

            # Step 6: Install dependencies (if packages.yml exists)
            packages_path = os.path.join(project_dir, 'packages.yml')
            if os.path.exists(packages_path):
                success, error = self._run_dbt_deps(project_dir, env)
                if not success:
                    result.error_message = f"Failed to install dbt dependencies: {error}"
                    return result

            # Step 7: Execute dbt command
            success, stdout, stderr = self._run_dbt_command(project_dir, env)

            # Append command output to logs
            if stdout:
                self._logs.append("--- dbt stdout ---")
                self._logs.append(stdout)
            if stderr:
                self._logs.append("--- dbt stderr ---")
                self._logs.append(stderr)

            # Step 8: Parse artifacts
            run_results = ArtifactParser.parse_run_results(project_dir)
            manifest = ArtifactParser.parse_manifest(project_dir)

            result.run_results_json = run_results
            result.manifest_json = manifest

            if run_results:
                stats = ArtifactParser.extract_stats(run_results)
                result.models_ran = stats['models_ran']
                result.models_passed = stats['models_passed']
                result.models_failed = stats['models_failed']
                result.models_skipped = stats['models_skipped']
                result.tests_passed = stats['tests_passed']
                result.tests_failed = stats['tests_failed']
                result.tests_warned = stats['tests_warned']

            # Step 9: Set final status
            if success:
                result.success = True
                self._log(f"dbt {self.config.command} completed successfully")
            else:
                result.success = False
                result.error_message = stderr or "dbt command failed"
                self._log(f"dbt {self.config.command} failed")

        except Exception as e:
            result.error_message = self.sanitizer.sanitize(str(e))
            self._log(f"Execution error: {result.error_message}")
            logger.exception("dbt execution failed")

        finally:
            # Step 10: Calculate duration and set logs
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at:
                result.duration_seconds = (result.completed_at - result.started_at).total_seconds()

            result.logs = self._get_logs()

            # Step 11: Cleanup
            self._cleanup()

        return result


def execute_dbt_run(
    git_repo_url: str,
    git_branch: str,
    command: str,
    target: str,
    git_subdirectory: Optional[str] = None,
    git_credentials: Optional[Dict[str, Any]] = None,
    select: Optional[str] = None,
    exclude: Optional[str] = None,
    full_refresh: bool = False,
    dbt_version: Optional[str] = None,
    profiles_yml: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
    timeout_seconds: int = MAX_EXECUTION_TIMEOUT_SECONDS,
) -> DbtExecutionResult:
    """
    Convenience function to execute a dbt run.

    This is the main entry point for executing dbt commands.

    Args:
        git_repo_url: URL of the git repository containing the dbt project
        git_branch: Branch to checkout
        command: dbt command to run (run, test, build, compile, seed, snapshot, docs, source)
        target: dbt target profile
        git_subdirectory: Optional subdirectory within the repo containing dbt project
        git_credentials: Optional dict with 'username', 'token', or 'ssh_key'
        select: dbt --select argument
        exclude: dbt --exclude argument
        full_refresh: Whether to use --full-refresh
        dbt_version: Optional specific dbt version (not currently used for installation)
        profiles_yml: Optional custom profiles.yml content
        env_vars: Optional environment variables for dbt
        timeout_seconds: Maximum execution time in seconds

    Returns:
        DbtExecutionResult with execution details and artifacts
    """
    config = DbtExecutionConfig(
        git_repo_url=git_repo_url,
        git_branch=git_branch,
        git_subdirectory=git_subdirectory,
        git_credentials=git_credentials,
        command=command,
        target=target,
        select=select,
        exclude=exclude,
        full_refresh=full_refresh,
        dbt_version=dbt_version,
        profiles_yml=profiles_yml,
        env_vars=env_vars,
        timeout_seconds=timeout_seconds,
    )

    executor = DbtExecutor(config)
    return executor.execute()
