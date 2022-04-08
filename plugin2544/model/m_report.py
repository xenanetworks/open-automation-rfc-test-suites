from pydantic import BaseModel
from ..utils.constants import (
    FramePacketTerminology,
    TestSuiteType,
    ThroughputUnit,
)


class ReportIdentification(BaseModel):
    customer_name: str
    customer_service_id: str
    customer_access_id: str
    comment: str


class ReportGenerationOptions(BaseModel):
    report_filename_prefix: str
    append_timestamp_to_filename: bool
    frame_packet_terminology: FramePacketTerminology
    include_detailed_port_info: bool
    include_stream_info: bool
    include_module_info: bool
    include_charts: bool
    throughput_unit_for_chart: ThroughputUnit
    pass_display_type: str


class ReportFormats(BaseModel):
    generate_pdf: bool
    generate_html: bool
    generate_xml: bool
    generate_csv: bool
    save_intermediate_results: bool
    add_precise_timestamp_for_each_line: bool
    intermediate_results_use_report_name_prefix: bool


class ReportTemplateConfig(BaseModel):
    description: str
    test_suite_type: TestSuiteType
    report_identification: ReportIdentification
    report_generation_options: ReportGenerationOptions
    report_formats: ReportFormats
