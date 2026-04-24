"""Config Analyzer — scans deployment config files for carbon-impacting issues."""

import re
import os
from typing import List, Union

from core.models import ConfigIssue, ErrorResponse

_CARBON_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _parse_dockerfile(dockerfile_path: str, workspace_root: str) -> List[ConfigIssue]:
    """Parse a Dockerfile and return a list of ConfigIssue objects."""
    issues = []

    try:
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return [ConfigIssue(
            issue_id="parse-error",
            file_path=dockerfile_path,
            line_number=0,
            description=f"Could not read Dockerfile: {e}",
            carbon_impact_score="HIGH",
            remediation="Ensure the Dockerfile is readable.",
            example_fix="",
        )]

    has_multistage = False
    copy_dot_line = None
    first_dep_install_line = None

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Check FROM instruction
        from_match = re.match(r'^FROM\s+(\S+)', stripped, re.IGNORECASE)
        if from_match:
            image = from_match.group(1)
            # Check for AS keyword (multi-stage)
            if re.search(r'\bAS\b', stripped, re.IGNORECASE):
                has_multistage = True
            # Check for unpinned tag: no colon or ends with :latest
            if ':' not in image or image.endswith(':latest'):
                issues.append(ConfigIssue(
                    issue_id="unpinned-base-image",
                    file_path=dockerfile_path,
                    line_number=lineno,
                    description=f"Base image '{image}' uses an unpinned or 'latest' tag.",
                    carbon_impact_score="HIGH",
                    remediation="Pin to a specific version using a minimal base image.",
                    example_fix="FROM python:3.12-slim",
                ))

        # Check COPY . . instruction
        if re.match(r'^COPY\s+\.\s+\.', stripped, re.IGNORECASE):
            if copy_dot_line is None:
                copy_dot_line = lineno

        # Check RUN instructions for dependency installs and npm flags
        if re.match(r'^RUN\s+', stripped, re.IGNORECASE):
            if re.search(r'npm\s+(install|ci)', stripped) or re.search(r'pip\s+install', stripped):
                if first_dep_install_line is None:
                    first_dep_install_line = lineno
            # Check npm install/ci without --omit=dev or --production
            if re.search(r'npm\s+(install|ci)', stripped):
                if '--omit=dev' not in stripped and '--production' not in stripped:
                    issues.append(ConfigIssue(
                        issue_id="dev-dependencies-included",
                        file_path=dockerfile_path,
                        line_number=lineno,
                        description="npm install/ci without --omit=dev ships development dependencies.",
                        carbon_impact_score="MEDIUM",
                        remediation="Add --omit=dev to exclude development dependencies from the production image.",
                        example_fix="RUN npm ci --omit=dev",
                    ))

    # Check COPY . . before dependency install
    if copy_dot_line is not None and first_dep_install_line is not None:
        if copy_dot_line < first_dep_install_line:
            issues.append(ConfigIssue(
                issue_id="suboptimal-copy-order",
                file_path=dockerfile_path,
                line_number=copy_dot_line,
                description="COPY . . appears before dependency installation, breaking layer cache.",
                carbon_impact_score="MEDIUM",
                remediation="Copy only dependency manifest files before running the install command to improve layer caching.",
                example_fix="COPY package*.json ./\nRUN npm ci --omit=dev\nCOPY . .",
            ))

    # Check for missing multi-stage build
    if not has_multistage:
        issues.append(ConfigIssue(
            issue_id="missing-multistage-build",
            file_path=dockerfile_path,
            line_number=1,
            description="Dockerfile does not use a multi-stage build.",
            carbon_impact_score="MEDIUM",
            remediation="Adopt a multi-stage build to reduce the final image size.",
            example_fix="FROM node:20-alpine AS deps\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci --omit=dev\n\nFROM node:20-alpine\nCOPY --from=deps /app/node_modules ./node_modules",
        ))

    # Check for missing .dockerignore
    dockerignore_path = os.path.join(os.path.dirname(dockerfile_path), ".dockerignore")
    if not os.path.exists(dockerignore_path):
        issues.append(ConfigIssue(
            issue_id="missing-dockerignore",
            file_path=dockerfile_path,
            line_number=0,
            description="No .dockerignore file found alongside the Dockerfile.",
            carbon_impact_score="HIGH",
            remediation="Create a .dockerignore file to exclude unnecessary files from the build context.",
            example_fix=".git\nnode_modules\n__pycache__\n*.pyc",
        ))

    return issues


def _parse_vercel_json(vercel_path: str) -> List[Union[ConfigIssue, ErrorResponse]]:
    """Parse vercel.json and detect always-on preview environments."""
    try:
        import json
        with open(vercel_path, "r", encoding="utf-8") as f:
            config = json.loads(f.read())
    except json.JSONDecodeError as e:
        return [ErrorResponse(
            tool="config_analyzer",
            message=f"Failed to parse {vercel_path}: {e}",
            error_type="ParseError",
        )]
    except Exception as e:
        return [ErrorResponse(
            tool="config_analyzer",
            message=f"Failed to read {vercel_path}: {e}",
            error_type="ParseError",
        )]

    issues = []
    github_config = config.get("github", {})
    if not github_config.get("cancelDeployment") and not github_config.get("silent"):
        issues.append(ConfigIssue(
            issue_id="always-on-preview",
            file_path=vercel_path,
            line_number=0,
            description="Vercel config does not disable always-on preview environments.",
            carbon_impact_score="LOW",
            remediation="Configure an inactivity shutdown policy for preview environments.",
            example_fix='{"github": {"silent": true, "cancelDeployment": true}}',
        ))
    return issues


def _parse_netlify_toml(netlify_path: str) -> List[Union[ConfigIssue, ErrorResponse]]:
    """Parse netlify.toml and detect always-on preview environments."""
    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(netlify_path, "rb") as f:
            config = tomllib.load(f)
    except Exception as e:
        return [ErrorResponse(
            tool="config_analyzer",
            message=f"Failed to parse {netlify_path}: {e}",
            error_type="ParseError",
        )]

    issues = []
    context = config.get("context", {})
    deploy_preview = context.get("deploy-preview", {})
    if deploy_preview and not deploy_preview.get("command", "").strip():
        issues.append(ConfigIssue(
            issue_id="always-on-preview",
            file_path=netlify_path,
            line_number=0,
            description="Netlify deploy preview context has no inactivity timeout configured.",
            carbon_impact_score="LOW",
            remediation="Configure an inactivity shutdown policy for preview environments.",
            example_fix='[context.deploy-preview]\n  command = "echo skip"',
        ))
    return issues


def _is_high_frequency_cron(cron_expr: str) -> bool:
    """Return True if the cron expression triggers more often than every 15 minutes."""
    parts = cron_expr.strip().split()
    if len(parts) < 5:
        return False
    minute_field = parts[0]
    # */N means every N minutes
    step_match = re.match(r'^\*/(\d+)$', minute_field)
    if step_match:
        step = int(step_match.group(1))
        return step < 15
    # Multiple comma-separated values: more than 4 per hour = more than every 15 min
    if ',' in minute_field:
        values = minute_field.split(',')
        if len(values) > 4:
            return True
    return False


def _parse_github_actions(workflow_path: str) -> List[Union[ConfigIssue, ErrorResponse]]:
    """Parse a GitHub Actions workflow file and detect high-frequency cron triggers."""
    try:
        import yaml
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [ErrorResponse(
            tool="config_analyzer",
            message=f"Failed to parse {workflow_path}: {e}",
            error_type="ParseError",
        )]
    except Exception as e:
        return [ErrorResponse(
            tool="config_analyzer",
            message=f"Failed to read {workflow_path}: {e}",
            error_type="ParseError",
        )]

    if not isinstance(workflow, dict):
        return []

    issues = []
    # PyYAML parses bare `on:` as boolean True; check both string and bool keys
    on_triggers = workflow.get("on", workflow.get(True, {}))
    if isinstance(on_triggers, dict):
        schedule = on_triggers.get("schedule", [])
        if isinstance(schedule, list):
            for entry in schedule:
                if isinstance(entry, dict):
                    cron_expr = entry.get("cron", "")
                    if cron_expr and _is_high_frequency_cron(cron_expr):
                        issues.append(ConfigIssue(
                            issue_id="high-frequency-cron",
                            file_path=workflow_path,
                            line_number=0,
                            description=f"Cron trigger '{cron_expr}' runs more frequently than every 15 minutes.",
                            carbon_impact_score="MEDIUM",
                            remediation="Reduce the cron trigger frequency to at least every 15 minutes.",
                            example_fix="schedule:\n  - cron: '*/15 * * * *'",
                        ))
    return issues


def analyze_configs(workspace_root: str) -> List[ConfigIssue]:
    """Scan workspace for deployment config files and return sorted ConfigIssue list."""
    all_issues = []

    # Scan for Dockerfile
    dockerfile_path = os.path.join(workspace_root, "Dockerfile")
    if os.path.exists(dockerfile_path):
        all_issues.extend(_parse_dockerfile(dockerfile_path, workspace_root))

    # Scan for vercel.json
    vercel_path = os.path.join(workspace_root, "vercel.json")
    if os.path.exists(vercel_path):
        results = _parse_vercel_json(vercel_path)
        for r in results:
            if isinstance(r, ConfigIssue):
                all_issues.append(r)
            # ErrorResponse: log but continue scanning

    # Scan for netlify.toml
    netlify_path = os.path.join(workspace_root, "netlify.toml")
    if os.path.exists(netlify_path):
        results = _parse_netlify_toml(netlify_path)
        for r in results:
            if isinstance(r, ConfigIssue):
                all_issues.append(r)

    # Scan for GitHub Actions workflows
    workflows_dir = os.path.join(workspace_root, ".github", "workflows")
    if os.path.isdir(workflows_dir):
        for filename in os.listdir(workflows_dir):
            if filename.endswith((".yml", ".yaml")):
                workflow_path = os.path.join(workflows_dir, filename)
                results = _parse_github_actions(workflow_path)
                for r in results:
                    if isinstance(r, ConfigIssue):
                        all_issues.append(r)

    # Sort by carbon_impact_score descending (HIGH > MEDIUM > LOW)
    all_issues.sort(key=lambda i: _CARBON_ORDER.get(i.carbon_impact_score, 99))

    return all_issues
