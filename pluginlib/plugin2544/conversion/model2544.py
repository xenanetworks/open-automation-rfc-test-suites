from typing import Dict, List
from pydantic import BaseModel, Field, NonNegativeInt, validator
from ..utils.field import MacAddress
from ..utils import constants as const
from . import enums


class LegacyPortRef(BaseModel):
    chassis_id: str = Field(alias="ChassisId")
    module_index: int = Field(alias="ModuleIndex")
    port_index: int = Field(alias="PortIndex")


class LegacyFrameSizesOptions(BaseModel):
    field_0: NonNegativeInt = Field(56, alias="0")
    field_1: NonNegativeInt = Field(60, alias="1")
    field_14: NonNegativeInt = Field(9216, alias="14")
    field_15: NonNegativeInt = Field(16360, alias="15")


class LegacyPortEntity(BaseModel):
    port_ref: LegacyPortRef = Field(alias="PortRef")
    port_group: const.PortGroup = Field(alias="PortGroup")
    pair_peer_ref: None = Field(alias="PairPeerRef")
    pair_peer_id: str = Field(alias="PairPeerId")
    multicast_role: str = Field(alias="MulticastRole")
    port_speed: const.PortSpeedStr = Field(alias="PortSpeed")
    inter_frame_gap: int = Field(alias="InterFrameGap")
    pause_mode_on: int = Field(alias="PauseModeOn")
    auto_neg_enabled: int = Field(alias="AutoNegEnabled")
    anlt_enabled: int = Field(alias="AnltEnabled")
    adjust_ppm: int = Field(alias="AdjustPpm")
    latency_offset: int = Field(alias="LatencyOffset")
    mdi_mdix_mode: const.MdiMdixMode = Field(alias="MdiMdixMode")
    fec_mode: enums.LegacyFecMode = Field(alias="FecMode")
    brr_mode: const.BRRModeStr = Field(alias="BrrMode")
    reply_arp_requests: int = Field(alias="ReplyArpRequests")
    reply_ping_requests: int = Field(alias="ReplyPingRequests")
    ip_v4_address: str = Field(alias="IpV4Address")
    ip_v4_routing_prefix: int = Field(alias="IpV4RoutingPrefix")
    ip_v4_gateway: str = Field(alias="IpV4Gateway")
    ip_v6_address: str = Field(alias="IpV6Address")
    ip_v6_routing_prefix: int = Field(alias="IpV6RoutingPrefix")
    ip_v6_gateway: str = Field(alias="IpV6Gateway")
    ip_gateway_mac_address: MacAddress = Field(alias="IpGatewayMacAddress")
    public_ip_address: str = Field(alias="PublicIpAddress")
    public_ip_routing_prefix: int = Field(alias="PublicIpRoutingPrefix")
    public_ip_address_v6: str = Field(alias="PublicIpAddressV6")
    public_ip_routing_prefix_v6: int = Field(alias="PublicIpRoutingPrefixV6")
    remote_loop_ip_address: str = Field(alias="RemoteLoopIpAddress")
    remote_loop_ip_address_v6: str = Field(alias="RemoteLoopIpAddressV6")
    remote_loop_mac_address: MacAddress = Field(alias="RemoteLoopMacAddress")
    enable_port_rate_cap: int = Field(alias="EnablePortRateCap")
    port_rate_cap_value: float = Field(alias="PortRateCapValue")
    port_rate_cap_profile: enums.LegacyPortRateCapProfile = Field(
        alias="PortRateCapProfile"
    )
    port_rate_cap_unit: enums.LegacyPortRateCapUnit = Field(alias="PortRateCapUnit")
    multi_stream_map: None = Field(alias="MultiStreamMap")
    item_id: str = Field(alias="ItemID")
    parent_id: str = Field(alias="ParentID")
    label: str = Field(alias="Label")

    @validator("remote_loop_mac_address", "ip_gateway_mac_address")
    def decode_mac_address(cls, v):
        v = base64.b64decode(v)
        v = "".join([hex(int(i)).replace("0x", "").zfill(2) for i in bytearray(v)])
        return MacAddress(v)


class LegacyPortHandler(BaseModel):
    entity_list: List[LegacyPortEntity] = Field(alias="EntityList")


class LegacyStreamConnectionList(BaseModel):
    connection_id: int = Field(alias="ConnectionId")
    port1_id: str = Field(alias="Port1Id")
    port2_id: str = Field(alias="Port2Id")
    address_offset1: int = Field(alias="AddressOffset1")
    address_offset2: int = Field(alias="AddressOffset2")
    item_id: str = Field(alias="ItemID")
    parent_id: str = Field(alias="ParentID")
    label: str = Field(alias="Label")


class LegacyStreamHandler(BaseModel):
    stream_connection_list: List[LegacyStreamConnectionList] = Field(
        alias="StreamConnectionList"
    )


import base64


class LegacyHeaderSegments(BaseModel):
    segment_value: str = Field(alias="SegmentValue")
    segment_type: enums.LegacySegmentType = Field(alias="SegmentType")
    item_id: str = Field(alias="ItemID")
    parent_id: str = Field(alias="ParentID")
    label: str = Field(alias="Label")

    @validator("segment_type", pre=True, always=True)
    def validate_segment_type(cls, v, values):
        if isinstance(v, str):
            if v.lower().startswith("raw"):
                return enums.LegacySegmentType(
                    f"raw_{len(values['segment_value']) // 2}"
                )
            else:
                return enums.LegacySegmentType(v)
        else:
            return v

    @validator("segment_value", pre=True, always=True)
    def decode_segment_value(cls, v):
        v = base64.b64decode(v)
        v = "".join([hex(int(i)).replace("0x", "").zfill(2) for i in bytearray(v)])
        return v


class LegacyPayloadDefinition(BaseModel):
    payload_type: str = Field(alias="PayloadType")
    payload_pattern: str = Field(alias="PayloadPattern")


class LegacyHwModifiers(BaseModel):
    offset: int = Field(alias="Offset")
    mask: str = Field(alias="Mask")
    action: enums.LegacyModifierActionOption = Field(alias="Action")
    start_value: int = Field(alias="StartValue")
    stop_value: int = Field(alias="StopValue")
    step_value: int = Field(alias="StepValue")
    repeat_count: int = Field(alias="RepeatCount")
    segment_id: str = Field(alias="SegmentId")
    field_name: str = Field(alias="FieldName")

    @validator("mask")
    def decode_segment_value(cls, v):
        v = base64.b64decode(v)
        v = "".join([hex(int(i)).replace("0x", "").zfill(2) for i in bytearray(v)])
        return v


class LegacyFieldValueRanges(BaseModel):
    start_value: int = Field(alias="StartValue")
    stop_value: int = Field(alias="StopValue")
    step_value: int = Field(alias="StepValue")
    action: enums.LegacyModifierActionOption = Field(alias="Action")
    reset_for_each_port: bool = Field(alias="ResetForEachPort")
    segment_id: str = Field(alias="SegmentId")
    field_name: str = Field(alias="FieldName")


class LegacyStreamConfig(BaseModel):
    sw_modifier: None = Field(alias="SwModifier")
    hw_modifiers: List[LegacyHwModifiers] = Field(alias="HwModifiers")
    field_value_ranges: List[LegacyFieldValueRanges] = Field(alias="FieldValueRanges")
    stream_descr_prefix: str = Field(alias="StreamDescrPrefix")
    resource_index: int = Field(alias="ResourceIndex")
    tpld_id: int = Field(alias="TpldId")
    enable_state: str = Field(alias="EnableState")
    rate_type: str = Field(alias="RateType")
    packet_limit: int = Field(alias="PacketLimit")
    rate_fraction: float = Field(alias="RateFraction")
    rate_pps: float = Field(alias="RatePps")
    rate_l2_mbps: float = Field(alias="RateL2Mbps")
    use_burst_values: bool = Field(alias="UseBurstValues")
    burst_size: int = Field(alias="BurstSize")
    burst_density: int = Field(alias="BurstDensity")
    header_segments: List[LegacyHeaderSegments] = Field(alias="HeaderSegments")
    packet_length_type: str = Field(alias="PacketLengthType")
    packet_min_size: int = Field(alias="PacketMinSize")
    packet_max_size: int = Field(alias="PacketMaxSize")
    payload_definition: LegacyPayloadDefinition = Field(alias="PayloadDefinition")
    resource_used: bool = Field(alias="ResourceUsed")
    child_resource_used: bool = Field(alias="ChildResourceUsed")


class LegacySteamEntity(BaseModel):
    stream_config: LegacyStreamConfig = Field(alias="StreamConfig")
    item_id: str = Field(alias="ItemID")
    parent_id: str = Field(alias="ParentID")
    label: str = Field(alias="Label")


class LegacyStreamProfileHandler(BaseModel):
    profile_assignment_map: Dict = Field(alias="ProfileAssignmentMap")
    entity_list: List[LegacySteamEntity] = Field(alias="EntityList")


class LegacyRateIterationOptions(BaseModel):
    search_type: enums.LegacySearchType = Field(alias="SearchType")
    acceptable_loss: float = Field(alias="AcceptableLoss")
    result_scope: enums.LegacyRateResultScopeType = Field(alias="ResultScope")
    fast_binary_search: bool = Field(alias="FastBinarySearch")
    initial_value: float = Field(alias="InitialValue")
    minimum_value: float = Field(alias="MinimumValue")
    maximum_value: float = Field(alias="MaximumValue")
    value_resolution: float = Field(alias="ValueResolution")
    use_pass_threshold: bool = Field(alias="UsePassThreshold")
    pass_threshold: float = Field(alias="PassThreshold")


class LegacyThroughput(BaseModel):
    type: str = Field(alias="$type")
    rate_iteration_options: LegacyRateIterationOptions = Field(
        alias="RateIterationOptions"
    )
    report_property_options: List = Field(alias="ReportPropertyOptions")
    test_type: enums.LegacyTestType = Field(alias="TestType")
    enabled: bool = Field(alias="Enabled")
    duration_type: enums.LegacyDurationType = Field(alias="DurationType")
    duration: float = Field(alias="Duration")
    duration_time_unit: const.DurationTimeUnit = Field(alias="DurationTimeUnit")
    duration_frames: int = Field(alias="DurationFrames")
    duration_frame_unit: enums.LegacyDurationFrameUnit = Field(
        alias="DurationFrameUnit"
    )
    iterations: int = Field(alias="Iterations")
    item_id: str = Field(alias="ItemID")
    parent_id: str = Field(alias="ParentID")
    label: str = Field(alias="Label")


class LegacyRateSweepOptions(BaseModel):
    start_value: float = Field(alias="StartValue")
    end_value: float = Field(alias="EndValue")
    step_value: float = Field(alias="StepValue")


class LegacyLatency(BaseModel):
    type: str = Field(alias="$type")
    rate_sweep_options: LegacyRateSweepOptions = Field(alias="RateSweepOptions")
    latency_mode: const.LatencyModeStr = Field(alias="LatencyMode")
    rate_relative_tput_max_rate: bool = Field(alias="RateRelativeTputMaxRate")
    test_type: enums.LegacyTestType = Field(alias="TestType")
    enabled: bool = Field(alias="Enabled")
    duration_type: enums.LegacyDurationType = Field(alias="DurationType")
    duration: float = Field(alias="Duration")
    duration_time_unit: const.DurationTimeUnit = Field(alias="DurationTimeUnit")
    duration_frames: int = Field(alias="DurationFrames")
    duration_frame_unit: enums.LegacyDurationFrameUnit = Field(
        alias="DurationFrameUnit"
    )
    iterations: int = Field(alias="Iterations")
    item_id: str = Field(alias="ItemID")
    parent_id: str = Field(alias="ParentID")
    label: str = Field(alias="Label")


class LegacyLoss(BaseModel):
    type: str = Field(alias="$type")
    rate_sweep_options: LegacyRateSweepOptions = Field(alias="RateSweepOptions")
    use_pass_fail_criteria: bool = Field(alias="UsePassFailCriteria")
    acceptable_loss: float = Field(alias="AcceptableLoss")
    acceptable_loss_type: str = Field(alias="AcceptableLossType")
    use_gap_monitor: bool = Field(alias="UseGapMonitor")
    gap_monitor_start: int = Field(alias="GapMonitorStart")
    gap_monitor_stop: int = Field(alias="GapMonitorStop")
    test_type: enums.LegacyTestType = Field(alias="TestType")
    enabled: bool = Field(alias="Enabled")
    duration_type: enums.LegacyDurationType = Field(alias="DurationType")
    duration: float = Field(alias="Duration")
    duration_time_unit: const.DurationTimeUnit = Field(alias="DurationTimeUnit")
    duration_frames: int = Field(alias="DurationFrames")
    duration_frame_unit: enums.LegacyDurationFrameUnit = Field(
        alias="DurationFrameUnit"
    )
    iterations: int = Field(alias="Iterations")
    item_id: str = Field(alias="ItemID")
    parent_id: str = Field(alias="ParentID")
    label: str = Field(alias="Label")


class LegacyBack2Back(BaseModel):
    type: str = Field(alias="$type")
    rate_sweep_options: LegacyRateSweepOptions = Field(alias="RateSweepOptions")
    result_scope: str = Field(alias="ResultScope")
    burst_resolution: float = Field(alias="BurstResolution")
    test_type: enums.LegacyTestType = Field(alias="TestType")
    enabled: bool = Field(alias="Enabled")
    duration_type: enums.LegacyDurationType = Field(alias="DurationType")
    duration: float = Field(alias="Duration")
    duration_time_unit: const.DurationTimeUnit = Field(alias="DurationTimeUnit")
    duration_frames: int = Field(alias="DurationFrames")
    duration_frame_unit: enums.LegacyDurationFrameUnit = Field(
        alias="DurationFrameUnit"
    )
    iterations: int = Field(alias="Iterations")
    item_id: str = Field(alias="ItemID")
    parent_id: str = Field(alias="ParentID")
    label: str = Field(alias="Label")


class LegacyTestTypeOptionMap(BaseModel):
    throughput: LegacyThroughput = Field(alias="Throughput")
    latency: LegacyLatency = Field(alias="Latency")
    loss: LegacyLoss = Field(alias="Loss")
    back2_back: LegacyBack2Back = Field(alias="Back2Back")


class LegacyMixedLengthConfig(BaseModel):
    frame_sizes: Dict = Field(alias="FrameSizes")


class LegacyPacketSizes(BaseModel):
    packet_size_type: enums.LegacyPacketSizeType = Field(alias="PacketSizeType")
    custom_packet_sizes: List = Field(alias="CustomPacketSizes")
    sw_packet_start_size: int = Field(alias="SwPacketStartSize")
    sw_packet_end_size: int = Field(alias="SwPacketEndSize")
    sw_packet_step_size: int = Field(alias="SwPacketStepSize")
    hw_packet_min_size: int = Field(alias="HwPacketMinSize")
    hw_packet_max_size: int = Field(alias="HwPacketMaxSize")
    mixed_sizes_weights: List = Field(alias="MixedSizesWeights")
    mixed_length_config: LegacyMixedLengthConfig = Field(alias="MixedLengthConfig")


class LegacyTopologyConfig(BaseModel):
    topology: const.TestTopology = Field(alias="Topology")
    direction: enums.LegacyTrafficDirection = Field(alias="Direction")


class LegacyFlowCreationOptions(BaseModel):
    flow_creation_type: enums.LegacyFlowCreationType = Field(alias="FlowCreationType")
    mac_base_address: str = Field(alias="MacBaseAddress")
    use_gateway_mac_as_dmac: bool = Field(alias="UseGatewayMacAsDmac")
    enable_multi_stream: bool = Field(alias="EnableMultiStream")
    per_port_stream_count: int = Field(alias="PerPortStreamCount")
    multi_stream_address_offset: int = Field(alias="MultiStreamAddressOffset")
    multi_stream_address_increment: int = Field(alias="MultiStreamAddressIncrement")
    multi_stream_mac_base_address: str = Field(alias="MultiStreamMacBaseAddress")
    use_micro_tpld_on_demand: bool = Field(alias="UseMicroTpldOnDemand")


class LegacyLearningOptions(BaseModel):
    mac_learning_mode: enums.LegacyMACLearningMode = Field(alias="MacLearningMode")
    mac_learning_retries: int = Field(alias="MacLearningRetries")
    arp_refresh_enabled: bool = Field(alias="ArpRefreshEnabled")
    arp_refresh_period: float = Field(alias="ArpRefreshPeriod")
    use_flow_based_learning_preamble: bool = Field(alias="UseFlowBasedLearningPreamble")
    flow_based_learning_frame_count: int = Field(alias="FlowBasedLearningFrameCount")
    flow_based_learning_delay: int = Field(alias="FlowBasedLearningDelay")
    learning_rate_percent: float = Field(alias="LearningRatePercent")
    learning_duration: float = Field(alias="LearningDuration")


class LegacyTestOptions(BaseModel):
    test_type_option_map: LegacyTestTypeOptionMap = Field(alias="TestTypeOptionMap")
    packet_sizes: LegacyPacketSizes = Field(alias="PacketSizes")
    topology_config: LegacyTopologyConfig = Field(alias="TopologyConfig")
    flow_creation_options: LegacyFlowCreationOptions = Field(
        alias="FlowCreationOptions"
    )
    learning_options: LegacyLearningOptions = Field(alias="LearningOptions")
    toggle_sync_state: bool = Field(alias="ToggleSyncState")
    sync_off_duration: int = Field(alias="SyncOffDuration")
    sync_on_duration: int = Field(alias="SyncOnDuration")
    payload_definition: LegacyPayloadDefinition = Field(alias="PayloadDefinition")
    enable_speed_reduct_sweep: bool = Field(alias="EnableSpeedReductSweep")
    use_port_sync_start: bool = Field(alias="UsePortSyncStart")
    port_stagger_steps: int = Field(alias="PortStaggerSteps")
    should_stop_on_los: bool = Field(alias="ShouldStopOnLos")
    port_reset_delay: int = Field(alias="PortResetDelay")
    outer_loop_mode: enums.LegacyOuterLoopMode = Field(alias="OuterLoopMode")


class LegacyChassisList(BaseModel):
    chassis_id: str = Field(alias="ChassisID")
    host_name: str = Field(alias="HostName")
    port_number: int = Field(alias="PortNumber")
    password: str = Field(alias="Password")
    connection_type: str = Field(alias="ConnectionType")
    used_module_list: List = Field(alias="UsedModuleList")
    resource_index: int = Field(alias="ResourceIndex")
    resource_used: bool = Field(alias="ResourceUsed")
    child_resource_used: bool = Field(alias="ChildResourceUsed")


class LegacyChassisManager(BaseModel):
    chassis_list: List[LegacyChassisList] = Field(alias="ChassisList")


class LegacyReportConfig(BaseModel):
    customer_name: str = Field(alias="CustomerName")
    customer_service_id: str = Field(alias="CustomerServiceID")
    customer_access_id: str = Field(alias="CustomerAccessID")
    comments: str = Field(alias="Comments")
    rate_unit_terminology: str = Field(alias="RateUnitTerminology")
    include_test_pair_info: bool = Field(alias="IncludeTestPairInfo")
    include_per_stream_info: bool = Field(alias="IncludePerStreamInfo")
    include_module_info: bool = Field(alias="IncludeModuleInfo")
    include_graphs: bool = Field(alias="IncludeGraphs")
    plot_throughput_unit: str = Field(alias="PlotThroughputUnit")
    pass_display_type: str = Field(alias="PassDisplayType")
    generate_pdf: bool = Field(alias="GeneratePdf")
    generate_html: bool = Field(alias="GenerateHtml")
    generate_xml: bool = Field(alias="GenerateXml")
    generate_csv: bool = Field(alias="GenerateCsv")
    save_intermediate_results: bool = Field(alias="SaveIntermediateResults")
    add_precise_timestamp_for_each_line: bool = Field(
        alias="AddPreciseTimestampForEachLine"
    )
    intermediate_results_use_report_name_prefix: bool = Field(
        alias="IntermediateResultsUseReportNamePrefix"
    )
    report_filename: str = Field(alias="ReportFilename")
    append_timestamp: bool = Field(alias="AppendTimestamp")


class LegacyModel2544(BaseModel):
    port_handler: LegacyPortHandler = Field(alias="PortHandler")
    stream_handler: LegacyStreamHandler = Field(alias="StreamHandler")
    stream_profile_handler: LegacyStreamProfileHandler = Field(
        alias="StreamProfileHandler"
    )
    test_options: LegacyTestOptions = Field(alias="TestOptions")
    creation_date: str = Field(alias="CreationDate")
    chassis_manager: LegacyChassisManager = Field(alias="ChassisManager")
    report_config: LegacyReportConfig = Field(alias="ReportConfig")
    tid_allocation_scope: enums.LegacyTidAllocationScope = Field(
        alias="TidAllocationScope"
    )
    format_version: int = Field(alias="FormatVersion")
    application_version: str = Field(alias="ApplicationVersion")
