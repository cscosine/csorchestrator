from dataclasses import dataclass
from typing import Generic, TypeVar

from csorchestrator.foundation.core.report import Report

T = TypeVar("T")


@dataclass
class OptionalResultWithReport(Generic[T]):
    """
    Collects an optional generic result and a report
    """

    report: Report
    result: T | None = None

    def has_result(self) -> bool:
        return self.result is not None

    def result_or(self, default: T) -> T:
        return self.result if self.result is not None else default

    @classmethod
    def create_result_and_report(cls, result: T, report: Report) -> "OptionalResultWithReport[T]":
        return cls(report, result)

    @classmethod
    def create_report(cls, report: Report) -> "OptionalResultWithReport[T]":
        return cls(report)
