from decimal import Decimal
from time import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
from dataclasses import asdict
from loguru import logger

from pluginlib.plugin2544.utils import exceptions
from .common import filter_port_structs
from ..utils.field import NonNegativeDecimal
from xoa_driver.utils import apply
from xoa_driver.ports import GenericL23Port
from xoa_driver.internals.core.commands import P_TRAFFIC, P_RECEIVESYNC

from .test_result_structure import ResultGroup, PortResult
from ..model import FrameLossRateTest
from .test_result_show import (
    show_all_frame_loss_result,
    show_all_latency_result,
    show_all_throughput_result,
    show_all_back_to_back_result,
    show_port_frame_loss_result,
    show_port_latency_result,
    show_port_throughput_result,
    show_port_back_to_back_result,
)
from .structure import TypeConf
from pluginlib.plugin2544.utils.constants import AcceptableLossType, TestType
from ..utils.logger import logger
from .test_result_structure import (
    AllResult,
    BoutEntry,
    StreamResult,
    TestPortParam,
)

if TYPE_CHECKING:
    from .structure import StreamInfo, PortStruct
    from .test_result_structure import (
        IterationEntry,
        ResultHandler,
        TestCommonParam,
    )
    from pluginlib.plugin2544.utils.logger import TestSuitPipe


# class StateChecker:
#     def __init__(
#         self, control_ports: List["PortStruct"], should_stop_on_los: bool
#     ) -> None:
#         self.should_stop_on_los = should_stop_on_los
#         self.started_dic = {}
#         self.sync_dic = {}
#         self.control_ports = control_ports
#         self.should_stop_on_los = should_stop_on_los

#     async def __ask(self):

#         if self.should_stop_on_los:
#             for port_struct in self.control_ports:
#                 port = port_struct.port_info.port
#                 self.sync_dic[port] = bool((await port.sync_status.get()).sync_status)
#                 port.on_receive_sync_change(self._change_sync_status)

#         for src_port_struct in filter_port_structs(self.control_ports):
#             src_port = src_port_struct.port_info.port
#             self.started_dic[src_port] = bool(
#                 (await src_port.traffic.state.get()).on_off
#             )
#             src_port.on_traffic_change(self._change_traffic_status)

#         return self

#     def __await__(self):
#         return self.__ask().__await__()

    # async def _change_sync_status(
    #     self, port: "GenericL23Port", get_attr: "P_RECEIVESYNC.GetDataAttr"
    # ) -> None:
    #     before = self.sync_dic[port]
    #     after = self.sync_dic[port] = bool(get_attr.sync_status)
    #     logger.warning(f"Change sync status from {before} to {after} ")
    #     if before and not after:
    #         raise exceptions.LossofPortSignal(port)

    # async def _change_traffic_status(
    #     self, port: "GenericL23Port", get_attr: "P_TRAFFIC.GetDataAttr"
    # ) -> None:
    #     before = self.started_dic[port]
    #     after = self.started_dic[port] = bool(get_attr.on_off)
    #     # logger.warning(f"Change traffic status for {before} to {after}")

    # def test_running(self) -> bool:
    #     return any(self.started_dic.values())

    # def los(self) -> bool:
    #     if self.should_stop_on_los:
    #         return not all(self.sync_dic.values())
    #     return False


# def should_quit(
#     state_checker: "StateChecker", start_time: float, actual_duration: Decimal
# ) -> bool:
#     test_finished = not state_checker.test_running()
#     elapsed = time() - start_time
#     actual_duration_elapsed = elapsed >= actual_duration + 5
#     los = state_checker.los()
#     if los:
#         logger.error("Test is stopped due to the loss of signal of ports.")
#     return test_finished or los or actual_duration_elapsed


async def generate_port_params(
    stream_lists: List["StreamInfo"],
    rate_percent_dic: Dict[str, "IterationEntry"],
) -> Dict[Tuple[str,], "TestPortParam"]:

    port_params = {}
    for stream_info in stream_lists:
        tx_port_struct = stream_info.port_struct
        port_index = tx_port_struct.properties.identity
        if (port_index,) in port_params:
            continue
        tx_inter_frame_gap = tx_port_struct.port_conf.inter_frame_gap
        tx_rate = get_port_rate(stream_info.port_struct, rate_percent_dic)
        tx_src_port_speed = await get_use_port_speed(stream_info.port_struct)
        port_params[(port_index,)] = TestPortParam(
            tx_inter_frame_gap, tx_rate, tx_src_port_speed
        )
        rx_port_list = stream_info.rx_ports
        for rx_port_struct in rx_port_list:
            peer_index = rx_port_struct.properties.identity
            rx_inter_frame_gap = rx_port_struct.port_conf.inter_frame_gap
            if (peer_index,) in port_params:
                continue
            rx_rate = get_port_rate(rx_port_struct, rate_percent_dic)
            rx_src_port_speed = await get_use_port_speed(rx_port_struct)
            port_params[(peer_index,)] = TestPortParam(
                rx_inter_frame_gap, rx_rate, rx_src_port_speed
            )

    return port_params


# async def get_port_speed(port_struct: "PortStruct") -> Decimal:
#     port = port_struct.port_info.port
#     port_conf = port_struct.port_conf
#     port_speed = (await port.speed.current.get()).port_speed * 1e6
#     if port_conf.port_rate_cap_profile.is_custom:
#         port_speed = min(port_conf.port_rate, port_speed)
#     return Decimal(str(port_speed))


# async def get_use_port_speed(port_struct: "PortStruct") -> NonNegativeDecimal:
#     port_conf = port_struct.port_conf
#     port_speed = await get_port_speed(port_struct)
#     if port_conf.peer_config_slot and len(port_struct.properties.peers) == 1:
#         peer_struct = port_struct.properties.peers[0]
#         peer_speed = await get_port_speed(peer_struct)
#         port_speed = min(port_speed, peer_speed)
#     port_speed = (
#         port_speed
#         * Decimal(str(1e6 - port_conf.speed_reduction_ppm))
#         / Decimal(str(1e6))
#     )
#     return NonNegativeDecimal(str(port_speed))


def get_port_rate(
    port_struct: "PortStruct", rate_percent_dic: Dict[str, "IterationEntry"]
) -> Decimal:
    return rate_percent_dic.get(
        port_struct.properties.identity, rate_percent_dic.get("all", BoutEntry())
    ).rate


def check_if_frame_loss_success(
    frame_loss_conf: "FrameLossRateTest", result: "AllResult"
) -> None:
    result.set_result_state(True)
    if frame_loss_conf.use_pass_fail_criteria:
        if frame_loss_conf.acceptable_loss_type == AcceptableLossType.PERCENT:
            if result.loss_ratio_pct > frame_loss_conf.acceptable_loss_pct:
                result.set_result_state(False)
        else:
            if result.loss_frames > frame_loss_conf.acceptable_loss_pct:
                result.set_result_state(False)


def avg_result(
    result_handler: "ResultHandler",
    max_iterations: int,
    type_conf: "TypeConf",
    xoa_out: "TestSuitPipe",
    current_packet_size: Optional[NonNegativeDecimal] = None,
) -> None:
    if max_iterations > 1:
        if current_packet_size is None:
            all_result = result_handler.all_result
            port_result = result_handler.port_result
            stream_result = result_handler.stream_result
        else:
            all_result = [
                x
                for x in result_handler.all_result
                if x.current_packet_size == current_packet_size
            ]
            port_result = [
                x
                for x in result_handler.port_result
                if x.current_packet_size == current_packet_size
            ]
            stream_result = [
                x
                for x in result_handler.stream_result
                if x.current_packet_size == current_packet_size
            ]

        average_all_result = AllResult.average(all_result)
        average_port_result = PortResult.average(port_result)
        average_stream_result = StreamResult.average(stream_result)
        result_handler.avg_all_result = list(average_all_result.values())
        result_handler.avg_port_result = list(average_port_result.values())
        result_group = ResultGroup(
            stream=average_stream_result,
            port=average_port_result,
            all=average_all_result,
        )

        if isinstance(type_conf, FrameLossRateTest):
            for final_result in result_group.all.values():
                check_if_frame_loss_success(type_conf, final_result)
        show_result(result_group, type_conf.test_type, xoa_out)


def show_result(
    result: "ResultGroup", test_type: "TestType", xoa_out: "TestSuitPipe"
) -> None:
    # logger.error(result)
    xoa_out.send_statistics(asdict(result))
    # if test_type == TestType.THROUGHPUT:
    #     show_all_throughput_result(result.all)
    #     show_port_throughput_result(result.port)
    # elif test_type == TestType.LATENCY_JITTER:
    #     show_all_latency_result(result.all)
    #     show_port_latency_result(result.port)
    # elif test_type == TestType.FRAME_LOSS_RATE:
    #     show_all_frame_loss_result(result.all)
    #     show_port_frame_loss_result(result.port)
    # elif test_type == TestType.BACK_TO_BACK:
    #     show_all_back_to_back_result(result.all)
    #     show_port_back_to_back_result(result.port)


async def aggregate_test_results(
    common_params: "TestCommonParam",
    stream_lists: List["StreamInfo"],
) -> "ResultGroup":

    current_packet_size = common_params.current_packet_size
    is_live = common_params.is_live
    test_result_state = common_params.test_result_state
    iteration = common_params.iteration

    tokens = []
    stream_result = {}
    ports_result = {}

    for stream_info in stream_lists:
        stream_id = stream_info.stream_id
        tpld_id = stream_info.tpldid
        tx_port = stream_info.port_struct.port
        port_index = stream_info.port_struct.properties.identity
        peer_index = stream_info.peer_struct.properties.identity

        burst_frames = Decimal(0)
        if (port_index, peer_index, stream_id, tpld_id) in common_params.stream_params:
            burst_frames = common_params.stream_params[
                (port_index, peer_index, stream_id, tpld_id)
            ].burst_frames
        else:
            burst_frames = Decimal("0")

        current_stream_result = StreamResult(
            port_index=port_index,
            peer_index=peer_index,
            stream_id=stream_id,
            tpld_id=tpld_id,
            is_live=is_live,
            current_packet_size=current_packet_size,
            test_result_state=test_result_state,
            rate=common_params.port_params[(port_index,)].rate,
            iteration=iteration,
            burst_frames=burst_frames,
        )
        stream_result[(stream_id, tpld_id)] = current_stream_result

        if (port_index,) in ports_result:
            current_port_result = ports_result[(port_index,)]
        else:
            current_port_result = ports_result[(port_index,)] = PortResult(
                port_index=port_index,
                is_live=is_live,
                current_packet_size=current_packet_size,
                iteration=iteration,
                test_result_state=test_result_state,
                rate=common_params.port_params[(port_index,)].rate,
                burst_frames=burst_frames,
            )
        pt_stream_index = len(tokens)
        pt_stream = tx_port.statistics.tx.obtain_from_stream(stream_id).get()
        current_stream_result.add_tx(pt_stream_index)
        current_port_result.add_tx(pt_stream_index)
        tokens.append(pt_stream)

        rx_port_list = stream_info.rx_ports
        for rx_port_struct in rx_port_list:
            rx_port = rx_port_struct.port

            real_peer_index = rx_port_struct.properties.identity
            if (real_peer_index,) not in ports_result:
                current_peer_result = ports_result[(real_peer_index,)] = PortResult(
                    port_index=real_peer_index,
                    is_live=is_live,
                    current_packet_size=current_packet_size,
                    iteration=iteration,
                    test_result_state=test_result_state,
                    rate=common_params.port_params[(real_peer_index,)].rate,
                    burst_frames=burst_frames,
                )
            else:
                current_peer_result = ports_result[(real_peer_index,)]
            tpld_obj = rx_port.statistics.rx.access_tpld(tpld_id=stream_info.tpldid)
            pr_tpldtraffic_index = len(tokens)
            pr_tpldtraffic = tpld_obj.traffic.get()
            current_stream_result.add_rx(pr_tpldtraffic_index)
            current_peer_result.add_rx(pr_tpldtraffic_index)
            tokens.append(pr_tpldtraffic)

            pr_tpldlatency = tpld_obj.latency.get()
            current_stream_result.add_la(len(tokens))
            current_peer_result.add_la(len(tokens))
            tokens.append(pr_tpldlatency)

            pr_tpldjitter = tpld_obj.jitter.get()
            current_stream_result.add_ji(len(tokens))
            current_peer_result.add_ji(len(tokens))
            tokens.append(pr_tpldjitter)

            pr_extra = rx_port.statistics.rx.extra.get()
            current_stream_result.add_ex(len(tokens))
            current_peer_result.add_ex(len(tokens))
            tokens.append(pr_extra)

            #  tx port should count for rr of its rx port
            pr_error = tpld_obj.errors.get()
            current_port_result.add_rr(pt_stream_index)
            current_port_result.add_rr(pr_tpldtraffic_index)
            current_port_result.add_rr(len(tokens))
            tokens.append(pr_error)

    replies = await apply(*tokens)
    for sr in stream_result.values():
        sr.read(replies, common_params)
    for pr in ports_result.values():
        pr.read(replies, common_params)

    all_result_value = AllResult(
        is_live=is_live,
        current_packet_size=current_packet_size,
        iteration=iteration,
        test_result_state=test_result_state,
    )
    all_result_value.read_from_ports(*ports_result.values())
    all_result = {("all",): all_result_value}
    return ResultGroup(stream_result, ports_result, all_result)


def set_test_state(result_group: ResultGroup, result_state: bool) -> None:
    if result_group:
        for i in result_group.all, result_group.port, result_group.stream:
            for v in i.values():
                v.set_result_state(result_state)
