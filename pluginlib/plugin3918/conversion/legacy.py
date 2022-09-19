import base64
from typing import Dict, List
from pydantic import BaseModel, Field, validator


class LegacyPortRef(BaseModel):
    legacy_chassis_id: str = Field(alias="ChassisId")
    legacy_module_index: int = Field(alias="ModuleIndex")
    legacy_port_index: int = Field(alias="PortIndex")


class BaseID(BaseModel):
    legacy_item_id: str = Field(alias="ItemID")
    legacy_parent_id: str = Field(alias="ParentID")
    legacy_label: str = Field(alias="Label")


class LegacyPortEntity(BaseID):
    legacy_port_ref: LegacyPortRef = Field(alias="PortRef")
    legacy_port_group: str = Field(alias="PortGroup")
    legacy_pair_peer_ref: None = Field(alias="PairPeerRef")
    legacy_pair_peer_id: str = Field(alias="PairPeerId")
    legacy_multicast_role: str = Field(alias="MulticastRole")
    legacy_port_speed: str = Field(alias="PortSpeed")
    legacy_inter_frame_gap: int = Field(alias="InterFrameGap")
    legacy_pause_mode_on: bool = Field(alias="PauseModeOn")
    legacy_auto_neg_enabled: bool = Field(alias="AutoNegEnabled")
    legacy_anlt_enabled: bool = Field(alias="AnltEnabled")
    legacy_adjust_ppm: int = Field(alias="AdjustPpm")
    legacy_latency_offset: int = Field(alias="LatencyOffset")
    legacy_mdi_mdix_mode: str = Field(alias="MdiMdixMode")
    legacy_fec_mode: str = Field(alias="FecMode")
    legacy_enable_fec: bool = Field(alias="EnableFec", default=False)
    legacy_brr_mode: str = Field(alias="BrrMode")
    legacy_reply_arp_requests: bool = Field(alias="ReplyArpRequests")
    legacy_reply_ping_requests: bool = Field(alias="ReplyPingRequests")
    legacy_ip_v4_address: str = Field(alias="IpV4Address")
    legacy_ip_v4_routing_prefix: int = Field(alias="IpV4RoutingPrefix")
    legacy_ip_v4_gateway: str = Field(alias="IpV4Gateway")
    legacy_ip_v6_address: str = Field(alias="IpV6Address")
    legacy_ip_v6_routing_prefix: int = Field(alias="IpV6RoutingPrefix")
    legacy_ip_v6_gateway: str = Field(alias="IpV6Gateway")
    legacy_ip_gateway_mac_address: str = Field(alias="IpGatewayMacAddress")
    legacy_public_ip_address: str = Field(alias="PublicIpAddress")
    legacy_public_ip_routing_prefix: int = Field(alias="PublicIpRoutingPrefix")
    legacy_public_ip_address_v6: str = Field(alias="PublicIpAddressV6")
    legacy_public_ip_routing_prefix_v6: int = Field(alias="PublicIpRoutingPrefixV6")
    legacy_remote_loop_ip_address: str = Field(alias="RemoteLoopIpAddress")
    legacy_remote_loop_ip_address_v6: str = Field(alias="RemoteLoopIpAddressV6")
    legacy_remote_loop_mac_address: str = Field(alias="RemoteLoopMacAddress")
    legacy_enable_port_rate_cap: int = Field(alias="EnablePortRateCap")
    legacy_port_rate_cap_value: float = Field(alias="PortRateCapValue")
    legacy_port_rate_cap_profile: str = Field(alias="PortRateCapProfile")
    legacy_port_rate_cap_unit: str = Field(alias="PortRateCapUnit")
    legacy_multi_stream_map: None = Field(alias="MultiStreamMap")
    # item_id: str = Field(alias="ItemID")
    # parent_id: str = Field(alias="ParentID")
    # label: str = Field(alias="Label")


class LegacyPortHandler(BaseModel):
    legacy_entity_list: List[LegacyPortEntity] = Field(alias="EntityList")


class LegacyPayloadDefinition(BaseModel):
    legacy_payload_type: str = Field(alias="PayloadType")
    legacy_payload_pattern: str = Field(alias="PayloadPattern")


class LegacyHeaderSegment(BaseID):
    legacy_segment_type: str = Field(alias="SegmentType")
    legacy_segment_value: str = Field(alias="SegmentValue")
    # item_id: str = Field(alias="ItemID")
    # parent_id: str = Field(alias="ParentID")
    # label: str = Field(alias="Label")


class LegacyHwModifiers(BaseModel):
    legacy_offset: int = Field(alias="Offset")
    legacy_mask: str = Field(alias="Mask")
    legacy_action: str = Field(alias="Action")
    legacy_start_value: int = Field(alias="StartValue")
    legacy_stop_value: int = Field(alias="StopValue")
    legacy_step_value: int = Field(alias="StepValue")
    legacy_repeat_count: int = Field(alias="RepeatCount")
    legacy_segment_id: str = Field(alias="SegmentId")
    legacy_field_name: str = Field(alias="FieldName")

    @validator("legacy_mask")
    def decode_segment_value(cls, v):
        v = base64.b64decode(v)
        v = "".join([hex(int(i)).replace("0x", "").zfill(2) for i in bytearray(v)])
        return v


class LegacyFieldValueRanges(BaseModel):
    legacy_start_value: int = Field(alias="StartValue")
    legacy_stop_value: int = Field(alias="StopValue")
    legacy_step_value: int = Field(alias="StepValue")
    legacy_action: str = Field(alias="Action")
    legacy_reset_for_each_port: bool = Field(alias="ResetForEachPort")
    legacy_segment_id: str = Field(alias="SegmentId")
    legacy_field_name: str = Field(alias="FieldName")


class LegacyStreamDefinition(BaseModel):
    # legacy_sw_modifier: None = Field(alias="SwModifier")
    # legacy_hw_modifiers: List[LegacyHwModifiers] = Field(alias="HwModifiers")
    # legacy_field_value_ranges: List[LegacyFieldValueRanges] = Field(
    #     alias="FieldValueRanges"
    # )
    legacy_stream_descr_prefix: str = Field(alias="StreamDescrPrefix")
    legacy_resource_index: int = Field(alias="ResourceIndex")
    legacy_tpld_id: int = Field(alias="TpldId")
    legacy_enable_state: str = Field(alias="EnableState")
    legacy_rate_type: str = Field(alias="RateType")
    legacy_packet_limit: int = Field(alias="PacketLimit")
    legacy_rate_fraction: float = Field(alias="RateFraction")
    legacy_rate_pps: float = Field(alias="RatePps")
    legacy_rate_l2_mbps: float = Field(alias="RateL2Mbps")
    legacy_use_burst_values: bool = Field(alias="UseBurstValues")
    legacy_burst_size: int = Field(alias="BurstSize")
    legacy_burst_density: int = Field(alias="BurstDensity")
    legacy_header_segments: List[LegacyHeaderSegment] = Field(alias="HeaderSegments")
    legacy_packet_length_type: str = Field(alias="PacketLengthType")
    legacy_packet_min_size: int = Field(alias="PacketMinSize")
    legacy_packet_max_size: int = Field(alias="PacketMaxSize")
    legacy_payload_definition: LegacyPayloadDefinition = Field(
        alias="PayloadDefinition"
    )
    legacy_resource_used: bool = Field(alias="ResourceUsed")
    legacy_child_resource_used: bool = Field(alias="ChildResourceUsed")


class LegacyMcTestDef(BaseID):
    legacy_comments: str = Field(alias="Comments")
    legacy_igmp_version: str = Field(alias="IgmpVersion")
    legacy_igmp_join_interval: int = Field(alias="IgmpJoinInterval")
    legacy_igmp_leave_interval: int = Field(alias="IgmpLeaveInterval")
    legacy_use_igmp_shaping: bool = Field(alias="UseIgmpShaping")
    legacy_use_igmp_source_address: bool = Field(alias="UseIgmpSourceAddress")
    legacy_force_leave_to_all_routers_group: bool = Field(
        alias="ForceLeaveToAllRoutersGroup"
    )
    legacy_max_igmp_frame_rate: float = Field(alias="MaxIgmpFrameRate")
    legacy_mc_ip_v4_start_address: str = Field(alias="McIpV4StartAddress")
    legacy_mc_ip_v6_start_address: str = Field(alias="McIpV6StartAddress")
    legacy_mc_address_step_value: int = Field(alias="McAddressStepValue")
    legacy_stream_definition: LegacyStreamDefinition = Field(alias="StreamDefinition")


class LegacyMcDefHandler(BaseModel):
    legacy_mc_test_def_list: List[LegacyMcTestDef] = Field(alias="McTestDefList")


class LegacyTopologyConfig(BaseModel):
    legacy_topology: str = Field(alias="Topology")
    legacy_direction: str = Field(alias="Direction")


class LegacyUnicastDef(BaseID):
    legacy_comments: str = Field(alias="Comments")
    legacy_topology_config: LegacyTopologyConfig = Field(alias="TopologyConfig")
    legacy_stream_definition: LegacyStreamDefinition = Field(alias="StreamDefinition")
    # item_id: str = Field(alias="ItemID")
    # parent_id: str = Field(alias="ParentID")
    # label: str = Field(alias="Label")


class LegacyUcDefHandler(BaseModel):
    legacy_unicast_def_list: List[LegacyUnicastDef] = Field(alias="UnicastDefList")


class BaseOptions(BaseModel):
    legacy_enabled: bool = Field(alias="Enabled")
    legacy_iterations: int = Field(alias="Iterations")
    legacy_duration: int = Field(alias="Duration")
    legacy_traffic_to_join_delay: int = Field(alias="TrafficToJoinDelay")
    legacy_join_to_traffic_delay: int = Field(alias="JoinToTrafficDelay")
    legacy_leave_to_stop_delay: int = Field(alias="LeaveToStopDelay")


class LegacyRateOptionsStartEndStep(BaseModel):
    legacy_start_value: float = Field(alias="StartValue")
    legacy_end_value: float = Field(alias="EndValue")
    legacy_step_value: float = Field(alias="StepValue")


class LegacyGroupJoinLeaveDelay(BaseOptions):
    legacy_rate_options: LegacyRateOptionsStartEndStep = Field(alias="RateOptions")
    # enabled: bool = Field(alias="Enabled")
    # iterations: int = Field(alias="Iterations")
    # duration: int = Field(alias="Duration")
    # traffic_to_join_delay: int = Field(alias="TrafficToJoinDelay")
    # join_to_traffic_delay: int = Field(alias="JoinToTrafficDelay")
    # leave_to_stop_delay: int = Field(alias="LeaveToStopDelay")


class LegacyMulticastGroupCapacity(BaseOptions):
    legacy_group_count_start: int = Field(alias="GroupCountStart")
    legacy_group_count_end: int = Field(alias="GroupCountEnd")
    legacy_group_count_step: int = Field(alias="GroupCountStep")
    legacy_rate_options: LegacyRateOptionsStartEndStep = Field(alias="RateOptions")
    # duration: int = Field(alias="Duration")
    # enabled: bool = Field(alias="Enabled")
    # iterations: int = Field(alias="Iterations")
    # traffic_to_join_delay: int = Field(alias="TrafficToJoinDelay")
    # join_to_traffic_delay: int = Field(alias="JoinToTrafficDelay")
    # leave_to_stop_delay: int = Field(alias="LeaveToStopDelay")


class LegacyRateOptionsInitialMinMax(BaseModel):
    legacy_initial_value: float = Field(alias="InitialValue")
    legacy_minimum_value: float = Field(alias="MinimumValue")
    legacy_maximum_value: float = Field(alias="MaximumValue")
    legacy_value_resolution: float = Field(alias="ValueResolution")
    legacy_use_pass_threshold: bool = Field(alias="UsePassThreshold")
    legacy_pass_threshold: float = Field(alias="PassThreshold")


class LegacyGroupCountDef(BaseModel):
    legacy_group_count_sel: str = Field(alias="GroupCountSel")
    legacy_group_count_start: int = Field(alias="GroupCountStart")
    legacy_group_count_end: int = Field(alias="GroupCountEnd")
    legacy_group_count_step: int = Field(alias="GroupCountStep")
    legacy_group_count_list: List[int] = Field(alias="GroupCountList")


class LegacyAggregatedThroughput(BaseOptions):
    legacy_rate_options: LegacyRateOptionsInitialMinMax = Field(alias="RateOptions")
    legacy_group_count_def: LegacyGroupCountDef = Field(alias="GroupCountDef")
    # enabled: bool = Field(alias="Enabled")
    # iterations: int = Field(alias="Iterations")
    # duration: int = Field(alias="Duration")
    # traffic_to_join_delay: int = Field(alias="TrafficToJoinDelay")
    # join_to_traffic_delay: int = Field(alias="JoinToTrafficDelay")
    # leave_to_stop_delay: int = Field(alias="LeaveToStopDelay")


class LegacyScaledGroupThroughput(BaseOptions):
    legacy_group_count_start: int = Field(alias="GroupCountStart")
    legacy_group_count_end: int = Field(alias="GroupCountEnd")
    legacy_group_count_step: int = Field(alias="GroupCountStep")
    legacy_use_max_capacity_result: bool = Field(alias="UseMaxCapacityResult")
    legacy_rate_options: LegacyRateOptionsStartEndStep = Field(alias="RateOptions")
    # enabled: bool = Field(alias="Enabled")
    # iterations: int = Field(alias="Iterations")
    # duration: int = Field(alias="Duration")
    # traffic_to_join_delay: int = Field(alias="TrafficToJoinDelay")
    # join_to_traffic_delay: int = Field(alias="JoinToTrafficDelay")
    # leave_to_stop_delay: int = Field(alias="LeaveToStopDelay")


class LegacyMixedClassThroughput(BaseOptions):
    legacy_rate_options: LegacyRateOptionsInitialMinMax = Field(alias="RateOptions")
    legacy_group_count_def: LegacyGroupCountDef = Field(alias="GroupCountDef")
    legacy_uc_traffic_load_ratio: float = Field(alias="UcTrafficLoadRatio")
    # enabled: bool = Field(alias="Enabled")
    # iterations: int = Field(alias="Iterations")
    # duration: int = Field(alias="Duration")
    # traffic_to_join_delay: int = Field(alias="TrafficToJoinDelay")
    # join_to_traffic_delay: int = Field(alias="JoinToTrafficDelay")
    # leave_to_stop_delay: int = Field(alias="LeaveToStopDelay")


class LegacyLatency(BaseOptions):
    legacy_rate_options: LegacyRateOptionsStartEndStep = Field(alias="RateOptions")
    legacy_group_count_def: LegacyGroupCountDef = Field(alias="GroupCountDef")
    # enabled: bool = Field(alias="Enabled")
    # iterations: int = Field(alias="Iterations")
    # duration: int = Field(alias="Duration")
    # traffic_to_join_delay: int = Field(alias="TrafficToJoinDelay")
    # join_to_traffic_delay: int = Field(alias="JoinToTrafficDelay")
    # leave_to_stop_delay: int = Field(alias="LeaveToStopDelay")


class LegacyBurdenedJoinDelay(BaseOptions):
    legacy_rate_options: LegacyRateOptionsStartEndStep = Field(alias="RateOptions")
    legacy_uc_traffic_load_ratio: float = Field(alias="UcTrafficLoadRatio")
    # enabled: bool = Field(alias="Enabled")
    # iterations: int = Field(alias="Iterations")
    # duration: int = Field(alias="Duration")
    # traffic_to_join_delay: int = Field(alias="TrafficToJoinDelay")
    # join_to_traffic_delay: int = Field(alias="JoinToTrafficDelay")
    # leave_to_stop_delay: int = Field(alias="LeaveToStopDelay")


class LegacyBurdenedLatency(LegacyLatency):
    legacy_uc_traffic_load_ratio: float = Field(alias="UcTrafficLoadRatio")


class LegacyTestTypeOptionMap(BaseModel):
    legacy_group_join_leave_delay: LegacyGroupJoinLeaveDelay = Field(
        alias="GroupJoinLeaveDelay"
    )
    legacy_multicast_group_capacity: LegacyMulticastGroupCapacity = Field(
        alias="GroupCapacity"
    )
    legacy_aggregated_throughput: LegacyAggregatedThroughput = Field(
        alias="AggregatedThroughput"
    )
    legacy_scaled_group_throughput: LegacyScaledGroupThroughput = Field(
        alias="ScaledGroupThroughput"
    )
    legacy_mixed_class_throughput: LegacyMixedClassThroughput = Field(
        alias="MixedClassThroughput"
    )
    legacy_latency: LegacyLatency = Field(alias="Latency")
    legacy_burdened_join_delay: LegacyBurdenedJoinDelay = Field(
        alias="BurdenedJoinDelay"
    )
    legacy_burdened_latency: LegacyBurdenedLatency = Field(alias="BurdenedLatency")


class LegacyMixedLengthConfig(BaseModel):
    legacy_frame_sizes: Dict[str, int] = Field(alias="FrameSizes")


class LegacyPacketSizes(BaseModel):
    legacy_packet_size_type: str = Field(alias="PacketSizeType")
    legacy_custom_packet_sizes: List[float] = Field(alias="CustomPacketSizes")
    legacy_sw_packet_start_size: int = Field(alias="SwPacketStartSize")
    legacy_sw_packet_end_size: int = Field(alias="SwPacketEndSize")
    legacy_sw_packet_step_size: int = Field(alias="SwPacketStepSize")
    legacy_hw_packet_min_size: int = Field(alias="HwPacketMinSize")
    legacy_hw_packet_max_size: int = Field(alias="HwPacketMaxSize")
    legacy_mixed_sizes_weights: List[int] = Field(alias="MixedSizesWeights")
    legacy_mixed_length_config: LegacyMixedLengthConfig = Field(
        alias="MixedLengthConfig"
    )


class LegacyFlowCreationOptions(BaseModel):
    legacy_flow_creation_type: str = Field(alias="FlowCreationType")
    legacy_mac_base_address: str = Field(alias="MacBaseAddress")
    legacy_use_gateway_mac_as_dmac: bool = Field(alias="UseGatewayMacAsDmac")
    legacy_enable_multi_stream: bool = Field(alias="EnableMultiStream")
    legacy_per_port_stream_count: int = Field(alias="PerPortStreamCount")
    legacy_multi_stream_address_offset: int = Field(alias="MultiStreamAddressOffset")
    legacy_multi_stream_address_increment: int = Field(
        alias="MultiStreamAddressIncrement"
    )
    legacy_multi_stream_mac_base_address: str = Field(alias="MultiStreamMacBaseAddress")
    legacy_use_micro_tpld_on_demand: bool = Field(alias="UseMicroTpldOnDemand")


class LegacyTestOptions3918(BaseModel):
    legacy_tid_offset: int = Field(alias="TidOffset")
    legacy_test_type_option_map: LegacyTestTypeOptionMap = Field(
        alias="TestTypeOptionMap"
    )
    legacy_packet_sizes: LegacyPacketSizes = Field(alias="PacketSizes")
    legacy_flow_creation_options: LegacyFlowCreationOptions = Field(
        alias="FlowCreationOptions"
    )
    legacy_latency_mode: str = Field(alias="LatencyMode")
    legacy_latency_display_unit: str = Field(alias="LatencyDisplayUnit")
    legacy_jitter_display_unit: str = Field(alias="JitterDisplayUnit")
    legacy_toggle_sync_state: bool = Field(alias="ToggleSyncState")
    legacy_sync_off_duration: int = Field(alias="SyncOffDuration")


class LegacyReportConfig(BaseModel):
    legacy_customer_name: str = Field(alias="CustomerName")
    legacy_customer_service_id: str = Field(alias="CustomerServiceID")
    legacy_customer_access_id: str = Field(alias="CustomerAccessID")
    legacy_comments: str = Field(alias="Comments")
    legacy_rate_unit_terminology: str = Field(alias="RateUnitTerminology")
    legacy_include_test_pair_info: bool = Field(alias="IncludeTestPairInfo")
    legacy_include_per_stream_info: bool = Field(alias="IncludePerStreamInfo")
    legacy_include_module_info: bool = Field(alias="IncludeModuleInfo")
    legacy_include_graphs: bool = Field(alias="IncludeGraphs")
    legacy_plot_throughput_unit: str = Field(alias="PlotThroughputUnit")
    legacy_pass_display_type: str = Field(alias="PassDisplayType")
    legacy_generate_pdf: bool = Field(alias="GeneratePdf")
    legacy_generate_html: bool = Field(alias="GenerateHtml")
    legacy_generate_xml: bool = Field(alias="GenerateXml")
    legacy_generate_csv: bool = Field(alias="GenerateCsv")
    legacy_save_intermediate_results: bool = Field(alias="SaveIntermediateResults")
    legacy_add_precise_timestamp_for_each_line: bool = Field(
        alias="AddPreciseTimestampForEachLine"
    )
    legacy_intermediate_results_use_report_name_prefix: bool = Field(
        alias="IntermediateResultsUseReportNamePrefix"
    )
    legacy_report_filename: str = Field(alias="ReportFilename")
    legacy_append_timestamp: bool = Field(alias="AppendTimestamp")


class LegacyChassis(BaseModel):
    legacy_chassis_id: str = Field(alias="ChassisID")
    legacy_host_name: str = Field(alias="HostName")
    legacy_port_number: int = Field(alias="PortNumber")
    legacy_password: str = Field(alias="Password")
    legacy_connection_type: str = Field(alias="ConnectionType")
    legacy_used_module_list: List = Field(alias="UsedModuleList")
    legacy_resource_index: int = Field(alias="ResourceIndex")
    legacy_resource_used: bool = Field(alias="ResourceUsed")
    legacy_child_resource_used: bool = Field(alias="ChildResourceUsed")


class LegacyChassisManager(BaseModel):
    legacy_chassis_list: List[LegacyChassis] = Field(alias="ChassisList")


class LegacyStreamEntity(BaseID):
    legacy_stream_config: LegacyStreamDefinition = Field(alias="StreamConfig")


class LegacyStreamProfileHandler(BaseModel):
    legacy_profile_assignment_map: Dict[str, str] = Field(alias="ProfileAssignmentMap")
    legacy_entity_list: List[LegacyStreamEntity] = Field(alias="EntityList")


class LegacyModel3918(BaseModel):
    legacy_port_handler: LegacyPortHandler = Field(alias="PortHandler")
    legacy_mc_def_handler: LegacyMcDefHandler = Field(alias="McDefHandler")
    legacy_uc_def_handler: LegacyUcDefHandler = Field(alias="UcDefHandler")
    legacy_test_options: LegacyTestOptions3918 = Field(alias="TestOptions")
    legacy_creation_date: str = Field(alias="CreationDate")
    legacy_stream_profile_handler: LegacyStreamProfileHandler = Field(
        alias="StreamProfileHandler"
    )
    legacy_chassis_manager: LegacyChassisManager = Field(alias="ChassisManager")
    legacy_report_config: LegacyReportConfig = Field(alias="ReportConfig")
    legacy_tid_allocation_scope: str = Field(alias="TidAllocationScope")
    legacy_format_version: int = Field(alias="FormatVersion")
    legacy_application_version: str = Field(alias="ApplicationVersion")
