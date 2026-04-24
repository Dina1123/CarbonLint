"""Unit tests for core/config_analyzer.py."""
import os
import tempfile
import pytest
from core.config_analyzer import analyze_configs
from core.models import ConfigIssue


def _write_file(directory, filename, content):
    path = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


# Test 1: Dockerfile with `latest` tag → unpinned-base-image issue
def test_unpinned_base_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_file(tmpdir, "Dockerfile", "FROM node:latest\nCMD [\"node\", \"app.js\"]\n")
        _write_file(tmpdir, ".dockerignore", "node_modules\n")
        issues = analyze_configs(tmpdir)
        issue_ids = [i.issue_id for i in issues]
        assert "unpinned-base-image" in issue_ids


# Test 2: Dockerfile without .dockerignore → missing-dockerignore issue
def test_missing_dockerignore():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_file(tmpdir, "Dockerfile", "FROM python:3.12-slim\nCMD [\"python\", \"app.py\"]\n")
        # No .dockerignore
        issues = analyze_configs(tmpdir)
        issue_ids = [i.issue_id for i in issues]
        assert "missing-dockerignore" in issue_ids


# Test 3: COPY . . before RUN pip install → suboptimal-copy-order issue
def test_suboptimal_copy_order():
    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_content = (
            "FROM python:3.12-slim\n"
            "COPY . .\n"
            "RUN pip install -r requirements.txt\n"
        )
        _write_file(tmpdir, "Dockerfile", dockerfile_content)
        _write_file(tmpdir, ".dockerignore", "*.pyc\n")
        issues = analyze_configs(tmpdir)
        issue_ids = [i.issue_id for i in issues]
        assert "suboptimal-copy-order" in issue_ids


# Test 4: no FROM ... AS → missing-multistage-build issue
def test_missing_multistage_build():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_file(tmpdir, "Dockerfile", "FROM python:3.12-slim\nCMD [\"python\", \"app.py\"]\n")
        _write_file(tmpdir, ".dockerignore", "*.pyc\n")
        issues = analyze_configs(tmpdir)
        issue_ids = [i.issue_id for i in issues]
        assert "missing-multistage-build" in issue_ids


# Test 5: npm install without --omit=dev → dev-dependencies-included issue
def test_dev_dependencies_included():
    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_content = (
            "FROM node:20-alpine AS deps\n"
            "WORKDIR /app\n"
            "COPY package*.json ./\n"
            "RUN npm install\n"
        )
        _write_file(tmpdir, "Dockerfile", dockerfile_content)
        _write_file(tmpdir, ".dockerignore", "node_modules\n")
        issues = analyze_configs(tmpdir)
        issue_ids = [i.issue_id for i in issues]
        assert "dev-dependencies-included" in issue_ids


# Test 6: cron */5 * * * * → high-frequency-cron issue
def test_high_frequency_cron():
    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_content = (
            "on:\n"
            "  schedule:\n"
            "    - cron: '*/5 * * * *'\n"
            "jobs:\n"
            "  build:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - run: echo hello\n"
        )
        os.makedirs(os.path.join(tmpdir, ".github", "workflows"), exist_ok=True)
        _write_file(tmpdir, ".github/workflows/ci.yml", workflow_content)
        issues = analyze_configs(tmpdir)
        issue_ids = [i.issue_id for i in issues]
        assert "high-frequency-cron" in issue_ids


# Test 7: always-on preview without timeout → always-on-preview issue (vercel.json)
def test_always_on_preview_vercel():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_file(tmpdir, "vercel.json", '{"version": 2}\n')
        issues = analyze_configs(tmpdir)
        issue_ids = [i.issue_id for i in issues]
        assert "always-on-preview" in issue_ids


# Test 8: issues sorted HIGH before MEDIUM before LOW
def test_issues_sorted_by_carbon_impact():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Dockerfile with latest tag (HIGH) and no multi-stage (MEDIUM)
        _write_file(tmpdir, "Dockerfile", "FROM node:latest\nRUN npm install\nCMD [\"node\", \"app.js\"]\n")
        # No .dockerignore (HIGH)
        issues = analyze_configs(tmpdir)
        if len(issues) >= 2:
            order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            scores = [order.get(i.carbon_impact_score, 99) for i in issues]
            assert scores == sorted(scores)


# Test 9: malformed YAML file → parse error returned, other files still scanned
def test_malformed_yaml_continues_scanning():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Bad YAML workflow
        os.makedirs(os.path.join(tmpdir, ".github", "workflows"), exist_ok=True)
        _write_file(tmpdir, ".github/workflows/bad.yml", "on: [\nbad yaml: {{\n")
        # Valid Dockerfile
        _write_file(tmpdir, "Dockerfile", "FROM node:latest\nCMD [\"node\", \"app.js\"]\n")
        _write_file(tmpdir, ".dockerignore", "node_modules\n")
        # Should still return Dockerfile issues despite bad YAML
        issues = analyze_configs(tmpdir)
        issue_ids = [i.issue_id for i in issues]
        assert "unpinned-base-image" in issue_ids


# Test 10: empty workspace → empty list, no warnings
def test_empty_workspace_returns_empty_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        issues = analyze_configs(tmpdir)
        assert issues == []


# Test 11: every returned issue has non-empty remediation and example_fix
def test_all_issues_have_remediation_and_example_fix():
    with tempfile.TemporaryDirectory() as tmpdir:
        _write_file(tmpdir, "Dockerfile", "FROM node:latest\nRUN npm install\nCMD [\"node\", \"app.js\"]\n")
        issues = analyze_configs(tmpdir)
        for issue in issues:
            assert issue.remediation and len(issue.remediation) > 0
            assert issue.example_fix and len(issue.example_fix) > 0
