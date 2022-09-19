import base64
import json
import hashlib
from typing import Any, Dict, List, Optional

from .enum_changer import AnyMember
from ..model.mc_uc_definition import McDefinition, UcFlowDefinition
from ..utils.field import MacAddress
from .legacy import (
    LegacyModel3918,
    LegacyPortEntity,
)
from ..model.port_config import (
    IPV4AddressProperties,
    IPV6AddressProperties,
    PortConfiguration,
)
from ..model.port_identity import PortIdentity
from ..model.test_config import FrameSizeConfiguration, FrameSizesOptions
from ..model.test_type_config import (
    AggregatedMulticastThroughput,
    BurdenedGroupJoinDelay,
    BurdenedMulticastLatency,
    GroupCountDef,
    MulticastLatency,
    MixedClassThroughput,
    RateOptionsInitialMinMax,
    TestTypeConfiguration3918,
    MulticastGroupCapacity,
    GroupJoinLeaveDelay,
    RateOptionsStartEndStep,
    ScaledGroupForwardingMatrix,
)
from ..model.test_suit import (
    TestConfiguration3918,
)
from ..model.protocol_segments import (
    ProtocolSegmentProfileConfig,
    HeaderSegment,
)
from ..utils.constants import (
    MIXED_DEFAULT_WEIGHTS,
    GroupCountSel,
    RBRRMode,
    RDisplayUnit,
    RFlowCreationType,
    RIgmpVersion,
    RLatencyMode,
    RMdiMdixMode,
    # RModifierAction,
    RPacketSizeType,
    RPayloadType,
    RPortRateCapProfile,
    RPortRateCapUnit,
    RPortSpeedMode,
    RProtocolOption,
    RRateType,
    RTestTopology,
    RTrafficDirection,
    RTidAllocationScope,
    RMulticastRole,
)
from ...plugin3918 import Model3918
from valhalla_core.core.test_suites.datasets import TestParameters
from pydantic.json import custom_pydantic_encoder


def model_3918_encoder(obj: Any):
    return custom_pydantic_encoder({AnyMember: lambda x: x.core}, obj)


class Converter:
    @staticmethod
    def convert_base_mac_address(mac_address: str):
        return ":".join(
            [
                hex(int(i)).replace("0x", "").zfill(2).upper()
                for i in mac_address.split(",")
            ]
        )

    def __init__(self, config_data, filepath=""):
        # self.id_map = {}
        if config_data:
            self.data = LegacyModel3918.parse_obj(config_data)
        elif filepath:
            self.data = LegacyModel3918.parse_file(filepath)
        else:
            raise Exception("Please check parameters")

    def __gen_profile(self) -> Dict[str, "ProtocolSegmentProfileConfig"]:
        stream_profile_handler = self.data.legacy_stream_profile_handler
        protocol_segments_profile = {}

        for profile in stream_profile_handler.legacy_entity_list:
            header_segments: List["HeaderSegment"] = []
            for hs in profile.legacy_stream_config.legacy_header_segments:
                header_segments.append(
                    HeaderSegment(
                        segment_type=hs.legacy_segment_type,
                        segment_value="".join(
                            [
                                hex(int(i)).replace("0x", "").zfill(2)
                                for i in bytearray(
                                    base64.b64decode(hs.legacy_segment_value)
                                )
                            ]
                        ),
                    )
                )
                protocol_segments_profile[
                    profile.legacy_item_id
                ] = ProtocolSegmentProfileConfig(
                    header_segments=header_segments,
                    payload_type=RPayloadType(
                        profile.legacy_stream_config.legacy_payload_definition.legacy_payload_type
                    ),
                    payload_pattern="0x"
                    + "".join(
                        [
                            hex(int(i)).replace("0x", "").zfill(2)
                            for i in profile.legacy_stream_config.legacy_payload_definition.legacy_payload_pattern.split(
                                ","
                            )
                        ]
                    ),
                    rate_type=RRateType(profile.legacy_stream_config.legacy_rate_type),
                    rate_fraction=profile.legacy_stream_config.legacy_rate_fraction,
                    rate_pps=profile.legacy_stream_config.legacy_rate_pps,
                )
        return protocol_segments_profile

    def __gen_port_identity(
        self, chassis_id_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, "PortIdentity"]:

        port_identity = {
            f"p{count}": PortIdentity(
                tester_id=chassis_id_map[p_info.legacy_port_ref.legacy_chassis_id][
                    "id"
                ],
                tester_index=chassis_id_map[p_info.legacy_port_ref.legacy_chassis_id][
                    "index"
                ],
                module_index=p_info.legacy_port_ref.legacy_module_index,
                port_index=p_info.legacy_port_ref.legacy_port_index,
            )
            for count, p_info in enumerate(
                self.data.legacy_port_handler.legacy_entity_list
            )
        }
        return port_identity

    def __gen_chassis_id_map(self) -> Dict[str, Dict[str, Any]]:
        return {
            chassis_info.legacy_chassis_id: {
                "id": hashlib.md5(
                    f"{chassis_info.legacy_host_name}:{chassis_info.legacy_port_number}".encode(
                        "utf-8"
                    )
                ).hexdigest(),
                "index": index,
            }
            for index, chassis_info in enumerate(
                self.data.legacy_chassis_manager.legacy_chassis_list
            )
        }

    def __gen_port_id_map(self, chassis_id_map) -> Dict[str, Dict[str, str]]:
        return {
            p_info.legacy_item_id: {
                "config": f"g-{chassis_id_map[p_info.legacy_port_ref.legacy_chassis_id]['index']}-{p_info.legacy_port_ref.legacy_module_index}-{p_info.legacy_port_ref.legacy_port_index}",
                "identity": f"p{count}",
            }
            for count, p_info in enumerate(
                self.data.legacy_port_handler.legacy_entity_list
            )
        }

    def __gen_ipv4_addr(self, entity: "LegacyPortEntity") -> "IPV4AddressProperties":
        return IPV4AddressProperties(
            address=(entity.legacy_ip_v4_address),
            routing_prefix=entity.legacy_ip_v4_routing_prefix,
            gateway=(entity.legacy_ip_v4_gateway)
            if entity.legacy_ip_v4_gateway
            else ("0.0.0.0"),
            public_address=(entity.legacy_public_ip_address)
            if entity.legacy_public_ip_address
            else ("0.0.0.0"),
            public_routing_prefix=entity.legacy_public_ip_routing_prefix,
            remote_loop_address=(entity.legacy_remote_loop_ip_address)
            if entity.legacy_remote_loop_ip_address
            else ("0.0.0.0"),
        )

    def __gen_ipv6_addr(self, entity: "LegacyPortEntity") -> "IPV6AddressProperties":
        return IPV6AddressProperties(
            address=(entity.legacy_ip_v6_address),
            routing_prefix=entity.legacy_ip_v6_routing_prefix,
            gateway=(entity.legacy_ip_v6_gateway)
            if entity.legacy_ip_v6_gateway
            else ("::"),
            public_address=entity.legacy_public_ip_address_v6
            if entity.legacy_public_ip_address_v6
            else ("::"),
            public_routing_prefix=entity.legacy_public_ip_routing_prefix_v6,
            remote_loop_address=(entity.legacy_remote_loop_ip_address_v6)
            if entity.legacy_remote_loop_ip_address_v6
            else ("::"),
        )

    def __gen_port_config(
        self,
        port_id_map: Dict[str, Dict[str, str]],
        protocol_segment: Dict[str, "ProtocolSegmentProfileConfig"],
    ) -> Dict[str, "PortConfiguration",]:
        return {
            port_id_map[entity.legacy_item_id]["config"]: PortConfiguration(
                port_slot=port_id_map[entity.legacy_item_id]["identity"],
                port_config_slot=port_id_map[entity.legacy_item_id]["config"],
                # port_group=PortGroup[entity.legacy_port_group],
                port_speed_mode=RPortSpeedMode(entity.legacy_port_speed),
                ipv4_properties=self.__gen_ipv4_addr(entity),
                ipv6_properties=self.__gen_ipv6_addr(entity),
                ip_gateway_mac_address=MacAddress.from_bytes(
                    base64.b64decode(entity.legacy_ip_gateway_mac_address)
                ),
                reply_arp_requests=bool(entity.legacy_reply_arp_requests),
                reply_ping_requests=bool(entity.legacy_reply_ping_requests),
                remote_loop_mac_address=MacAddress.from_bytes(
                    base64.b64decode(entity.legacy_remote_loop_mac_address)
                ),
                inter_frame_gap=entity.legacy_inter_frame_gap,
                speed_reduction_ppm=entity.legacy_adjust_ppm,
                pause_mode_enabled=entity.legacy_pause_mode_on,
                latency_offset_ms=entity.legacy_latency_offset,
                fec_mode=entity.legacy_enable_fec,
                port_rate_cap_enabled=bool(entity.legacy_enable_port_rate_cap),
                port_rate_cap_value=entity.legacy_port_rate_cap_value,
                port_rate_cap_profile=RPortRateCapProfile(
                    entity.legacy_port_rate_cap_profile
                ),
                port_rate_cap_unit=RPortRateCapUnit(entity.legacy_port_rate_cap_unit),
                auto_neg_enabled=bool(entity.legacy_auto_neg_enabled),
                anlt_enabled=bool(entity.legacy_anlt_enabled),
                mdi_mdix_mode=RMdiMdixMode(entity.legacy_mdi_mdix_mode),
                broadr_reach_mode=RBRRMode(entity.legacy_brr_mode),
                profile=(
                    protocol_segment[
                        self.data.legacy_stream_profile_handler.legacy_profile_assignment_map[
                            f"guid_{entity.legacy_item_id}"
                        ]
                    ]
                ),
                multicast_role=RMulticastRole(entity.legacy_multicast_role),
            )
            for entity in self.data.legacy_port_handler.legacy_entity_list
        }

    def __gen_frame_size(self):
        packet_size = self.data.legacy_test_options.legacy_packet_sizes
        fz = packet_size.legacy_mixed_length_config.legacy_frame_sizes
        return FrameSizeConfiguration(
            packet_size_type=RPacketSizeType(packet_size.legacy_packet_size_type),
            custom_packet_sizes=packet_size.legacy_custom_packet_sizes,
            fixed_packet_start_size=packet_size.legacy_sw_packet_start_size,
            fixed_packet_end_size=packet_size.legacy_sw_packet_end_size,
            fixed_packet_step_size=packet_size.legacy_sw_packet_step_size,
            varying_packet_min_size=packet_size.legacy_hw_packet_min_size,
            varying_packet_max_size=packet_size.legacy_hw_packet_max_size,
            mixed_sizes_weights=packet_size.legacy_mixed_sizes_weights
            if packet_size.legacy_mixed_sizes_weights
            else MIXED_DEFAULT_WEIGHTS,
            mixed_length_config=FrameSizesOptions(
                field_0=fz.get("0", 56),
                field_1=fz.get("1", 60),
                field_14=fz.get("14", 9216),
                field_15=fz.get("15", 16360),
            ),
        )

    def __gen_test_config(self) -> "TestConfiguration3918":
        test_options = self.data.legacy_test_options
        flow_option = test_options.legacy_flow_creation_options
        return TestConfiguration3918(
            tid_offset=test_options.legacy_tid_offset,
            flow_creation_type=RFlowCreationType(flow_option.legacy_flow_creation_type),
            mac_base_address=self.convert_base_mac_address(
                flow_option.legacy_mac_base_address
            ),
            use_gateway_mac_as_dmac=flow_option.legacy_use_gateway_mac_as_dmac,
            enable_multi_stream=flow_option.legacy_enable_multi_stream,
            per_port_stream_count=flow_option.legacy_per_port_stream_count,
            multi_stream_address_offset=flow_option.legacy_multi_stream_address_offset,
            multi_stream_address_increment=flow_option.legacy_multi_stream_address_increment,
            multi_stream_mac_base_address=self.convert_base_mac_address(
                flow_option.legacy_multi_stream_mac_base_address
            ),
            use_micro_tpld_on_demand=flow_option.legacy_use_micro_tpld_on_demand,
            latency_mode=RLatencyMode(test_options.legacy_latency_mode),
            latency_display_unit=RDisplayUnit(test_options.legacy_latency_display_unit),
            jitter_display_unit=RDisplayUnit(test_options.legacy_jitter_display_unit),
            toggle_sync_state=test_options.legacy_toggle_sync_state,
            sync_off_duration=test_options.legacy_sync_off_duration,
            tid_allocation_scope=RTidAllocationScope(
                self.data.legacy_tid_allocation_scope
            ),
            frame_sizes=self.__gen_frame_size(),
        )

    def __gen_group_join_leave_delay(self) -> Optional["GroupJoinLeaveDelay"]:
        group_join_leave_delay = (
            self.data.legacy_test_options.legacy_test_type_option_map.legacy_group_join_leave_delay
        )
        return (
            GroupJoinLeaveDelay(
                iterations=group_join_leave_delay.legacy_iterations,
                duration=group_join_leave_delay.legacy_duration,
                traffic_to_join_delay=group_join_leave_delay.legacy_traffic_to_join_delay,
                join_to_traffic_delay=group_join_leave_delay.legacy_join_to_traffic_delay,
                leave_to_stop_delay=group_join_leave_delay.legacy_leave_to_stop_delay,
                rate_options=RateOptionsStartEndStep(
                    start_value=group_join_leave_delay.legacy_rate_options.legacy_start_value,
                    end_value=group_join_leave_delay.legacy_rate_options.legacy_end_value,
                    step_value=group_join_leave_delay.legacy_rate_options.legacy_step_value,
                ),
            )
            if group_join_leave_delay.legacy_enabled
            else None
        )

    def __gen_multicast_group_capacity(self) -> Optional["MulticastGroupCapacity"]:
        multicast_group_capacity = (
            self.data.legacy_test_options.legacy_test_type_option_map.legacy_multicast_group_capacity
        )
        return (
            MulticastGroupCapacity(
                group_count_start=multicast_group_capacity.legacy_group_count_start,
                group_count_end=multicast_group_capacity.legacy_group_count_end,
                group_count_step=multicast_group_capacity.legacy_group_count_step,
                rate_options=RateOptionsStartEndStep(
                    start_value=multicast_group_capacity.legacy_rate_options.legacy_start_value,
                    end_value=multicast_group_capacity.legacy_rate_options.legacy_end_value,
                    step_value=multicast_group_capacity.legacy_rate_options.legacy_step_value,
                ),
                iterations=multicast_group_capacity.legacy_iterations,
                duration=multicast_group_capacity.legacy_duration,
                traffic_to_join_delay=multicast_group_capacity.legacy_traffic_to_join_delay,
                join_to_traffic_delay=multicast_group_capacity.legacy_join_to_traffic_delay,
                leave_to_stop_delay=multicast_group_capacity.legacy_leave_to_stop_delay,
            )
            if multicast_group_capacity.legacy_enabled
            else None
        )

    def __gen_aggregated_throughput(self) -> Optional["AggregatedMulticastThroughput"]:
        aggregated_throughput = (
            self.data.legacy_test_options.legacy_test_type_option_map.legacy_aggregated_throughput
        )
        return (
            AggregatedMulticastThroughput(
                rate_options=RateOptionsInitialMinMax(
                    initial_value=aggregated_throughput.legacy_rate_options.legacy_initial_value,
                    minimum_value=aggregated_throughput.legacy_rate_options.legacy_minimum_value,
                    maximum_value=aggregated_throughput.legacy_rate_options.legacy_maximum_value,
                    value_resolution=aggregated_throughput.legacy_rate_options.legacy_value_resolution,
                    use_pass_threshold=aggregated_throughput.legacy_rate_options.legacy_use_pass_threshold,
                    pass_threshold=aggregated_throughput.legacy_rate_options.legacy_pass_threshold,
                ),
                group_count_def=GroupCountDef(
                    group_count_sel=GroupCountSel(
                        aggregated_throughput.legacy_group_count_def.legacy_group_count_sel
                    ),
                    group_count_start=aggregated_throughput.legacy_group_count_def.legacy_group_count_start,
                    group_count_end=aggregated_throughput.legacy_group_count_def.legacy_group_count_end,
                    group_count_step=aggregated_throughput.legacy_group_count_def.legacy_group_count_step,
                    group_count_list=aggregated_throughput.legacy_group_count_def.legacy_group_count_list,
                ),
                iterations=aggregated_throughput.legacy_iterations,
                duration=aggregated_throughput.legacy_duration,
                traffic_to_join_delay=aggregated_throughput.legacy_traffic_to_join_delay,
                join_to_traffic_delay=aggregated_throughput.legacy_join_to_traffic_delay,
                leave_to_stop_delay=aggregated_throughput.legacy_leave_to_stop_delay,
            )
            if aggregated_throughput.legacy_enabled
            else None
        )

    def __gen_scaled_group_throughput(self) -> Optional["ScaledGroupForwardingMatrix"]:
        scaled_group_throughput = (
            self.data.legacy_test_options.legacy_test_type_option_map.legacy_scaled_group_throughput
        )
        return (
            ScaledGroupForwardingMatrix(
                group_count_start=scaled_group_throughput.legacy_group_count_start,
                group_count_end=scaled_group_throughput.legacy_group_count_end,
                group_count_step=scaled_group_throughput.legacy_group_count_step,
                use_max_capacity_result=scaled_group_throughput.legacy_use_max_capacity_result,
                rate_options=RateOptionsStartEndStep(
                    start_value=scaled_group_throughput.legacy_rate_options.legacy_start_value,
                    end_value=scaled_group_throughput.legacy_rate_options.legacy_end_value,
                    step_value=scaled_group_throughput.legacy_rate_options.legacy_step_value,
                ),
                iterations=scaled_group_throughput.legacy_iterations,
                duration=scaled_group_throughput.legacy_duration,
                traffic_to_join_delay=scaled_group_throughput.legacy_traffic_to_join_delay,
                join_to_traffic_delay=scaled_group_throughput.legacy_join_to_traffic_delay,
                leave_to_stop_delay=scaled_group_throughput.legacy_leave_to_stop_delay,
            )
            if scaled_group_throughput.legacy_enabled
            else None
        )

    def __gen_mixed_class_throughput(self) -> Optional["MixedClassThroughput"]:
        mixed_class_throughput = (
            self.data.legacy_test_options.legacy_test_type_option_map.legacy_mixed_class_throughput
        )
        return (
            MixedClassThroughput(
                rate_options=RateOptionsInitialMinMax(
                    initial_value=mixed_class_throughput.legacy_rate_options.legacy_initial_value,
                    minimum_value=mixed_class_throughput.legacy_rate_options.legacy_minimum_value,
                    maximum_value=mixed_class_throughput.legacy_rate_options.legacy_maximum_value,
                    value_resolution=mixed_class_throughput.legacy_rate_options.legacy_value_resolution,
                    use_pass_threshold=mixed_class_throughput.legacy_rate_options.legacy_use_pass_threshold,
                    pass_threshold=mixed_class_throughput.legacy_rate_options.legacy_pass_threshold,
                ),
                uc_traffic_load_ratio=mixed_class_throughput.legacy_uc_traffic_load_ratio,
                group_count_def=GroupCountDef(
                    group_count_sel=GroupCountSel(
                        mixed_class_throughput.legacy_group_count_def.legacy_group_count_sel
                    ),
                    group_count_start=mixed_class_throughput.legacy_group_count_def.legacy_group_count_start,
                    group_count_end=mixed_class_throughput.legacy_group_count_def.legacy_group_count_end,
                    group_count_step=mixed_class_throughput.legacy_group_count_def.legacy_group_count_step,
                    group_count_list=mixed_class_throughput.legacy_group_count_def.legacy_group_count_list,
                ),
                iterations=mixed_class_throughput.legacy_iterations,
                duration=mixed_class_throughput.legacy_duration,
                traffic_to_join_delay=mixed_class_throughput.legacy_traffic_to_join_delay,
                join_to_traffic_delay=mixed_class_throughput.legacy_join_to_traffic_delay,
                leave_to_stop_delay=mixed_class_throughput.legacy_leave_to_stop_delay,
            )
            if mixed_class_throughput.legacy_enabled
            else None
        )

    def __gen_multicast_latency(self) -> Optional["MulticastLatency"]:
        latency = (
            self.data.legacy_test_options.legacy_test_type_option_map.legacy_latency
        )
        return (
            MulticastLatency(
                rate_options=RateOptionsStartEndStep(
                    start_value=latency.legacy_rate_options.legacy_start_value,
                    end_value=latency.legacy_rate_options.legacy_end_value,
                    step_value=latency.legacy_rate_options.legacy_step_value,
                ),
                group_count_def=GroupCountDef(
                    group_count_sel=GroupCountSel(
                        latency.legacy_group_count_def.legacy_group_count_sel
                    ),
                    group_count_start=latency.legacy_group_count_def.legacy_group_count_start,
                    group_count_end=latency.legacy_group_count_def.legacy_group_count_end,
                    group_count_step=latency.legacy_group_count_def.legacy_group_count_step,
                    group_count_list=latency.legacy_group_count_def.legacy_group_count_list,
                ),
                iterations=latency.legacy_iterations,
                duration=latency.legacy_duration,
                traffic_to_join_delay=latency.legacy_traffic_to_join_delay,
                join_to_traffic_delay=latency.legacy_join_to_traffic_delay,
                leave_to_stop_delay=latency.legacy_leave_to_stop_delay,
            )
            if latency.legacy_enabled
            else None
        )

    def __gen_burdened_group_join_delay(self) -> Optional["BurdenedGroupJoinDelay"]:
        burdened_join_delay = (
            self.data.legacy_test_options.legacy_test_type_option_map.legacy_burdened_join_delay
        )
        return (
            BurdenedGroupJoinDelay(
                rate_options=RateOptionsStartEndStep(
                    start_value=burdened_join_delay.legacy_rate_options.legacy_start_value,
                    end_value=burdened_join_delay.legacy_rate_options.legacy_end_value,
                    step_value=burdened_join_delay.legacy_rate_options.legacy_step_value,
                ),
                uc_traffic_load_ratio=burdened_join_delay.legacy_uc_traffic_load_ratio,
                iterations=burdened_join_delay.legacy_iterations,
                duration=burdened_join_delay.legacy_duration,
                traffic_to_join_delay=burdened_join_delay.legacy_traffic_to_join_delay,
                join_to_traffic_delay=burdened_join_delay.legacy_join_to_traffic_delay,
                leave_to_stop_delay=burdened_join_delay.legacy_leave_to_stop_delay,
            )
            if burdened_join_delay.legacy_enabled
            else None
        )

    def __gen_burdened_multicast_latency(self) -> Optional["BurdenedMulticastLatency"]:
        burdened_latency = (
            self.data.legacy_test_options.legacy_test_type_option_map.legacy_burdened_latency
        )
        return (
            BurdenedMulticastLatency(
                rate_options=RateOptionsStartEndStep(
                    start_value=burdened_latency.legacy_rate_options.legacy_start_value,
                    end_value=burdened_latency.legacy_rate_options.legacy_end_value,
                    step_value=burdened_latency.legacy_rate_options.legacy_step_value,
                ),
                group_count_def=GroupCountDef(
                    group_count_sel=GroupCountSel(
                        burdened_latency.legacy_group_count_def.legacy_group_count_sel
                    ),
                    group_count_start=burdened_latency.legacy_group_count_def.legacy_group_count_start,
                    group_count_end=burdened_latency.legacy_group_count_def.legacy_group_count_end,
                    group_count_step=burdened_latency.legacy_group_count_def.legacy_group_count_step,
                    group_count_list=burdened_latency.legacy_group_count_def.legacy_group_count_list,
                ),
                uc_traffic_load_ratio=burdened_latency.legacy_uc_traffic_load_ratio,
                iterations=burdened_latency.legacy_iterations,
                duration=burdened_latency.legacy_duration,
                traffic_to_join_delay=burdened_latency.legacy_traffic_to_join_delay,
                join_to_traffic_delay=burdened_latency.legacy_join_to_traffic_delay,
                leave_to_stop_delay=burdened_latency.legacy_leave_to_stop_delay,
            )
            if burdened_latency.legacy_enabled
            else None
        )

    def __gen_test_type_config(self):
        return TestTypeConfiguration3918(
            group_join_leave_delay=self.__gen_group_join_leave_delay(),
            multicast_group_capacity=self.__gen_multicast_group_capacity(),
            aggregated_multicast_throughput=self.__gen_aggregated_throughput(),
            scaled_group_forwarding_matrix=self.__gen_scaled_group_throughput(),
            mixed_class_throughput=self.__gen_mixed_class_throughput(),
            multicast_latency=self.__gen_multicast_latency(),
            burdened_group_join_delay=self.__gen_burdened_group_join_delay(),
            burdened_multicast_latency=self.__gen_burdened_multicast_latency(),
        )

    def __gen_mc_definition(
        self, protocol_segments: Dict[str, ProtocolSegmentProfileConfig]
    ):
        mc_def = self.data.legacy_mc_def_handler.legacy_mc_test_def_list[0]
        mc_def_seg = mc_def.legacy_stream_definition
        uc_def = self.data.legacy_uc_def_handler.legacy_unicast_def_list[0]
        uc_def_seg = uc_def.legacy_stream_definition
        profile_id = self.data.legacy_stream_profile_handler.legacy_profile_assignment_map[
            f"guid_{self.data.legacy_port_handler.legacy_entity_list[0].legacy_item_id}"
        ]

        mc_profile_id = self.data.legacy_stream_profile_handler.legacy_profile_assignment_map[f"guid_{mc_def.legacy_item_id}"]
        # uc_profile_id = self.data.legacy_stream_profile_handler.legacy_profile_assignment_map[f"guid_{uc_def.legacy_item_id}"]

        mc_seg_result = protocol_segments[mc_profile_id].copy()
        uc_seg_result = protocol_segments[profile_id].copy()

        mc_seg_result.payload_type = RPayloadType(
            mc_def_seg.legacy_payload_definition.legacy_payload_type
        )
        mc_seg_result.payload_pattern = (
            "0x"
            + bytes(
                [
                    int(i)
                    for i in mc_def_seg.legacy_payload_definition.legacy_payload_pattern.split(
                        ","
                    )
                ]
            ).hex()
        )
        mc_seg_result.rate_type = RRateType(mc_def_seg.legacy_rate_type)
        mc_seg_result.rate_fraction = mc_def_seg.legacy_rate_fraction
        mc_seg_result.rate_pps = mc_def_seg.legacy_rate_pps

        uc_seg_result.payload_type = RPayloadType(
            uc_def_seg.legacy_payload_definition.legacy_payload_type
        )
        uc_seg_result.payload_pattern = (
            "0x"
            + bytes(
                [
                    int(i)
                    for i in uc_def_seg.legacy_payload_definition.legacy_payload_pattern.split(
                        ","
                    )
                ]
            ).hex()
        )
        uc_seg_result.rate_type = RRateType(uc_def_seg.legacy_rate_type)
        uc_seg_result.rate_fraction = uc_def_seg.legacy_rate_fraction
        uc_seg_result.rate_pps = uc_def_seg.legacy_rate_pps

        return McDefinition(
            comments=mc_def.legacy_comments,
            igmp_version=RIgmpVersion(mc_def.legacy_igmp_version),
            igmp_join_interval=mc_def.legacy_igmp_join_interval,
            igmp_leave_interval=mc_def.legacy_igmp_leave_interval,
            use_igmp_shaping=mc_def.legacy_use_igmp_shaping,
            use_igmp_source_address=mc_def.legacy_use_igmp_source_address,
            force_leave_to_all_routers_group=mc_def.legacy_force_leave_to_all_routers_group,
            max_igmp_frame_rate=mc_def.legacy_max_igmp_frame_rate,
            mc_ip_v4_start_address=(mc_def.legacy_mc_ip_v4_start_address),
            mc_ip_v6_start_address=(mc_def.legacy_mc_ip_v6_start_address),
            mc_address_step_value=mc_def.legacy_mc_address_step_value,
            stream_definition=mc_seg_result,
            uc_flow_def=UcFlowDefinition(
                comment=uc_def.legacy_comments,
                topology=RTestTopology(uc_def.legacy_topology_config.legacy_topology),
                direction=RTrafficDirection(
                    uc_def.legacy_topology_config.legacy_direction
                ),
                stream_definition=uc_seg_result,
            ),
            item_id=mc_def.legacy_item_id,
        )

    def gen(self) -> "TestParameters":
        tester_id_map = self.__gen_chassis_id_map()
        port_id_map = self.__gen_port_id_map(tester_id_map)
        protocol_segments = self.__gen_profile()
        return TestParameters(
            username="3918",
            port_identities=self.__gen_port_identity(tester_id_map),
            config=Model3918(
                mc_definition=self.__gen_mc_definition(protocol_segments),
                protocol_segments=protocol_segments,
                ports_configuration=self.__gen_port_config(
                    port_id_map, protocol_segments
                ),
                test_configuration=self.__gen_test_config(),
                test_types_configuration=self.__gen_test_type_config(),
            ),
        )
