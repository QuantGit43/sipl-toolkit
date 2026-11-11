"""Діагностика (помилки й попередження) з прив'язкою до позиції в тексті."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ast import SourceSpan


@dataclass
class Diagnostic:
    code: str
    message: str
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    severity: str = "error"

    @classmethod
    def at_span(cls, code: str, message: str, span: SourceSpan | None) -> Diagnostic:
        if span is None:
            return cls(code, message, 1, 1)
        return cls(code, message, span.line, span.column, span.end_line, span.end_column)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }

    def format(self, filename: str = "<input>") -> str:
        return f"{filename}:{self.line}:{self.column}: {self.severity}[{self.code}]: {self.message}"


class SiplError(Exception):
    """Базовий виняток SIPL; містить одну або кілька діагностик."""

    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics
        super().__init__("; ".join(d.message for d in diagnostics))


class SiplSyntaxError(SiplError):
    pass
