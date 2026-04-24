"""Data models for the Carbon-Aware Code Optimizer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Metrics:
    execution_time_ms: float
    memory_used_bytes: int
    energy_kwh: float
    co2_grams: float

    def to_dict(self) -> dict:
        return {
            "execution_time_ms": self.execution_time_ms,
            "memory_used_bytes": self.memory_used_bytes,
            "energy_kwh": self.energy_kwh,
            "co2_grams": self.co2_grams,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Metrics":
        return cls(
            execution_time_ms=d["execution_time_ms"],
            memory_used_bytes=d["memory_used_bytes"],
            energy_kwh=d["energy_kwh"],
            co2_grams=d["co2_grams"],
        )


@dataclass
class FunctionInfo:
    name: str
    complexity_score: int
    line_start: int
    line_end: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "complexity_score": self.complexity_score,
            "line_start": self.line_start,
            "line_end": self.line_end,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FunctionInfo":
        return cls(
            name=d["name"],
            complexity_score=d["complexity_score"],
            line_start=d["line_start"],
            line_end=d["line_end"],
        )


@dataclass
class Issue:
    issue_id: str
    severity: str
    line_number: int
    description: str
    suggested_fix: str
    carbon_impact_score: str

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity,
            "line_number": self.line_number,
            "description": self.description,
            "suggested_fix": self.suggested_fix,
            "carbon_impact_score": self.carbon_impact_score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Issue":
        return cls(
            issue_id=d["issue_id"],
            severity=d["severity"],
            line_number=d["line_number"],
            description=d["description"],
            suggested_fix=d["suggested_fix"],
            carbon_impact_score=d["carbon_impact_score"],
        )


@dataclass
class AnalysisResult:
    functions: list[FunctionInfo] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    parse_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "functions": [f.to_dict() for f in self.functions],
            "issues": [i.to_dict() for i in self.issues],
            "parse_time_ms": self.parse_time_ms,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AnalysisResult":
        return cls(
            functions=[FunctionInfo.from_dict(f) for f in d.get("functions", [])],
            issues=[Issue.from_dict(i) for i in d.get("issues", [])],
            parse_time_ms=d.get("parse_time_ms", 0.0),
        )


@dataclass
class Change:
    pass_name: str
    description: str
    line_number: int

    def to_dict(self) -> dict:
        return {
            "pass_name": self.pass_name,
            "description": self.description,
            "line_number": self.line_number,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Change":
        return cls(
            pass_name=d["pass_name"],
            description=d["description"],
            line_number=d["line_number"],
        )


@dataclass
class OptimizationResult:
    optimized_code: str
    changes: list[Change] = field(default_factory=list)
    expected_improvement_percent: float = 0.0

    def to_dict(self) -> dict:
        return {
            "optimized_code": self.optimized_code,
            "changes": [c.to_dict() for c in self.changes],
            "expected_improvement_percent": self.expected_improvement_percent,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "OptimizationResult":
        return cls(
            optimized_code=d["optimized_code"],
            changes=[Change.from_dict(c) for c in d.get("changes", [])],
            expected_improvement_percent=d.get("expected_improvement_percent", 0.0),
        )


@dataclass
class Comparison:
    execution_time_improvement_pct: float
    memory_improvement_pct: float
    co2_improvement_pct: float
    summary: str

    def to_dict(self) -> dict:
        return {
            "execution_time_improvement_pct": self.execution_time_improvement_pct,
            "memory_improvement_pct": self.memory_improvement_pct,
            "co2_improvement_pct": self.co2_improvement_pct,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Comparison":
        return cls(
            execution_time_improvement_pct=d["execution_time_improvement_pct"],
            memory_improvement_pct=d["memory_improvement_pct"],
            co2_improvement_pct=d["co2_improvement_pct"],
            summary=d["summary"],
        )


@dataclass
class Report:
    analysis: AnalysisResult
    original_metrics: Metrics
    optimized_code: str
    optimized_metrics: Metrics
    comparison: Comparison

    def to_dict(self) -> dict:
        return {
            "analysis": self.analysis.to_dict(),
            "original_metrics": self.original_metrics.to_dict(),
            "optimized_code": self.optimized_code,
            "optimized_metrics": self.optimized_metrics.to_dict(),
            "comparison": self.comparison.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Report":
        return cls(
            analysis=AnalysisResult.from_dict(d["analysis"]),
            original_metrics=Metrics.from_dict(d["original_metrics"]),
            optimized_code=d["optimized_code"],
            optimized_metrics=Metrics.from_dict(d["optimized_metrics"]),
            comparison=Comparison.from_dict(d["comparison"]),
        )


@dataclass
class ErrorResponse:
    tool: str
    message: str
    error: bool = True
    error_type: str = ""

    def to_dict(self) -> dict:
        return {
            "error": self.error,
            "tool": self.tool,
            "message": self.message,
            "error_type": self.error_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ErrorResponse":
        return cls(
            error=d.get("error", True),
            tool=d.get("tool", ""),
            message=d.get("message", ""),
            error_type=d.get("error_type", ""),
        )


@dataclass
class MCPSuggestion:
    server: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "server": self.server,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MCPSuggestion":
        return cls(
            server=d["server"],
            reason=d["reason"],
        )


@dataclass
class StruggleSignal:
    signal_type: str
    severity: str
    message: str
    mcp_suggestion: Optional[MCPSuggestion] = None

    def to_dict(self) -> dict:
        return {
            "signal_type": self.signal_type,
            "severity": self.severity,
            "message": self.message,
            "mcp_suggestion": self.mcp_suggestion.to_dict() if self.mcp_suggestion is not None else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StruggleSignal":
        mcp = d.get("mcp_suggestion")
        return cls(
            signal_type=d["signal_type"],
            severity=d["severity"],
            message=d["message"],
            mcp_suggestion=MCPSuggestion.from_dict(mcp) if mcp is not None else None,
        )


@dataclass
class ConfigIssue:
    issue_id: str
    file_path: str
    line_number: int
    description: str
    carbon_impact_score: str
    remediation: str
    example_fix: str

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "description": self.description,
            "carbon_impact_score": self.carbon_impact_score,
            "remediation": self.remediation,
            "example_fix": self.example_fix,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConfigIssue":
        return cls(
            issue_id=d["issue_id"],
            file_path=d["file_path"],
            line_number=d["line_number"],
            description=d["description"],
            carbon_impact_score=d["carbon_impact_score"],
            remediation=d["remediation"],
            example_fix=d["example_fix"],
        )
