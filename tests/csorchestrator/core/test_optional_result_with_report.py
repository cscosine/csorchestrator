from csorchestrator.foundation.core.optional_result_with_report import OptionalResultWithReport
from csorchestrator.foundation.core.report import Report


def test_optional_result_with_report() -> None:
    report = Report()
    report.append_error("fail")
    report.append_warning("be careful")
    report.append_info("info")

    report_without_result: OptionalResultWithReport[int] = OptionalResultWithReport.create_report(report)
    assert not report_without_result.has_result()

    assert report_without_result.result_or(33) == 33
    assert len(report_without_result.report.errors) == 1
    assert len(report_without_result.report.warnings) == 1
    assert len(report_without_result.report.infos) == 1

    optional_result_with_report = OptionalResultWithReport[int].create_result_and_report(42, report)
    assert optional_result_with_report.has_result()
    assert optional_result_with_report.result == 42
    assert optional_result_with_report.result_or(33) == 42

    assert len(optional_result_with_report.report.errors) == 1
    assert len(optional_result_with_report.report.warnings) == 1
    assert len(optional_result_with_report.report.infos) == 1

    # test using constructor
    report_without_result = OptionalResultWithReport(report)
    assert not report_without_result.has_result()

    assert report_without_result.result_or(33) == 33
    assert len(report_without_result.report.errors) == 1
    assert len(report_without_result.report.warnings) == 1
    assert len(report_without_result.report.infos) == 1

    optional_result_with_report = OptionalResultWithReport[int](report, 42)
    assert optional_result_with_report.has_result()
    assert optional_result_with_report.result == 42
    assert optional_result_with_report.result_or(33) == 42

    assert len(optional_result_with_report.report.errors) == 1
    assert len(optional_result_with_report.report.warnings) == 1
    assert len(optional_result_with_report.report.infos) == 1
