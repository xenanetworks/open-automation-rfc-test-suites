from decimal import Decimal
from time import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from loguru import logger
from .common import get_source_port_structs
from ..utils.field import NonNegativeDecimal
from xoa_driver.utils import apply
from xoa_driver.ports import GenericL23Port
from xoa_driver.internals.core.commands import P_TRAFFIC, P_RECEIVESYNC

from .test_result_structure import ResultGroup, PortResult, Result
from ..model import BackToBackTest, FrameLossRateTest, LatencyTest, ThroughputTest
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
from ..utils.constants import AcceptableLossType
from ..utils.logger import logger
from .test_result_structure import (
    AllResult,
    BoutEntry,
    StreamResult,
    TestPortParam,
)

if TYPE_CHECKING:
    from .structure import StreamInfo, Structure
    from .test_result_structure import (
        IterationEntry,
        ResultHandler,
        TestCommonParam,
    )


class StateChecker:
    def __init__(
        self, control_ports: List["Structure"], should_stop_on_los: bool
    ) -> None:
        source_port_structs = get_source_port_structs(control_ports)
        self.should_stop_on_los = should_stop_on_los
        self.started_dic = {}
        self.sync_dic = {}
        if should_stop_on_los:
            for port_struct in control_ports:
                self.sync_dic[port_struct.port] = True
                port_struct.port.on_receive_sync_change(self._change_sync_status)

        for src_port_struct in source_port_structs:
            self.started_dic[src_port_struct.port] = True
            src_port_struct.port.on_traffic_change(self._change_traffic_status)

    async def _change_sync_status(
        self, port: "GenericL23Port", get_attr: "P_RECEIVESYNC.GetDataAttr"
    ) -> None:
        before = self.sync_dic[port]
        after = self.sync_dic[port] = bool(get_attr.sync_status)
        logger.error(f"Change sync status from {before} to {after} ")

    async def _change_traffic_status(
        self, port: "GenericL23Port", get_attr: "P_TRAFFIC.GetDataAttr"
    ) -> None:
        before = self.started_dic[port]
        after = self.started_dic[port] = bool(get_attr.on_off)
        logger.error(f"Change traffic status for {before} to {after}")

    def test_running(self) -> bool:
        running = any(self.started_dic.values())
       
        return running

    def los(self) -> bool:
        if self.should_stop_on_los:
            return all(self.sync_dic.values()) 
        return False

def should_quit(state_checker:"StateChecker", start_time:float, actual_duration: Decimal):
    test_finished = not state_checker.test_running()
    elapsed = time() - start_time
    actual_duration_elapsed = (elapsed >= actual_duration)
    los = state_checker.los()
    if los:
        logger.error("Test is stopped due to the loss of signal of ports.")
    should_quit = test_finished or los or actual_duration_elapsed
    return should_quit



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


async def get_port_speed(port_struct: "Structure") -> Decimal:
    port = port_struct.port
    port_conf = port_struct.port_conf
    port_speed = (await port.speed.current.get()).port_speed * 1e6
    if port_conf.port_rate_cap_profile.is_custom:
        port_speed = min(port_conf.port_rate, port_speed)
    return Decimal(str(port_speed))


async def get_use_port_speed(port_struct: "Structure") -> NonNegativeDecimal:
    port_conf = port_struct.port_conf
    port_speed = await get_port_speed(port_struct)
    if port_conf.peer_config_slot and len(port_struct.properties.peers) == 1:
        peer_struct = port_struct.properties.peers[0]
        peer_speed = await get_port_speed(peer_struct)
        port_speed = min(port_speed, peer_speed)
    port_speed = (
        port_speed
        * Decimal(str(1e6 - port_conf.speed_reduction_ppm))
        / Decimal(str(1e6))
    )
    return NonNegativeDecimal(str(port_speed))


def get_port_rate(
    port_struct: "Structure", rate_percent_dic: Dict[str, "IterationEntry"]
) -> Decimal:
    return rate_percent_dic.get(
        port_struct.properties.identity, rate_percent_dic.get("all", BoutEntry())
    ).rate


def check_if_frame_loss_success(
    frame_loss_conf: "FrameLossRateTest", result: "AllResult"
):
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
    current_packet_size: Optional[NonNegativeDecimal] = None,
) -> None:
    pass
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
        result_group = ResultGroup(
            stream=average_stream_result,
            port=average_port_result,
            all=average_all_result,
        )

        if isinstance(type_conf, ThroughputTest):
            show_type = "throughput"
        elif isinstance(type_conf, LatencyTest):
            show_type = "latency"
        elif isinstance(type_conf, FrameLossRateTest):
            show_type = "frame_loss"
            for final_result in result_group.all.values():
                check_if_frame_loss_success(type_conf, final_result)
        elif isinstance(type_conf, BackToBackTest):
            show_type = "back_to_back"
        show_result(result_group, show_type)


def show_result(result: "ResultGroup", show_type: str) -> None:
    if show_type == "throughput":
        show_all_throughput_result(result.all)
        show_port_throughput_result(result.port)
    elif show_type == "latency":
        show_all_latency_result(result.all)
        show_port_latency_result(result.port)
    elif show_type == "frame_loss":
        show_all_frame_loss_result(result.all)
        show_port_frame_loss_result(result.port)
    elif show_type == "back_to_back":
        show_all_back_to_back_result(result.all)
        show_port_back_to_back_result(result.port)


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
        port_index = stream_info.port_struct.properties.identity
        stream_id = stream_info.stream_id
        tx_port = stream_info.port_struct.port
        rx_port_list = stream_info.rx_ports
        for rx_port_struct in rx_port_list:
            rx_port = rx_port_struct.port
            peer_index = rx_port_struct.properties.identity

            tpld = rx_port.statistics.rx.access_tpld(tpld_id=stream_info.tpldid)
            if (port_index, peer_index, stream_id) in common_params.stream_params:
                burst_frames = common_params.stream_params[
                    (port_index, peer_index, stream_id)
                ].burst_frames
            else:
                burst_frames = Decimal("0")
            current_stream_result = StreamResult(
                port_index=port_index,
                peer_index=peer_index,
                stream_id=stream_id,
                is_live=is_live,
                current_packet_size=current_packet_size,
                test_result_state=test_result_state,
                rate=common_params.port_params[(port_index,)].rate,
                iteration=iteration,
                burst_frames=burst_frames,
            )
            stream_result[(port_index, peer_index, stream_id)] = current_stream_result

            if (port_index,) not in ports_result:
                current_port_result = PortResult(
                    port_index=port_index,
                    is_live=is_live,
                    current_packet_size=current_packet_size,
                    iteration=iteration,
                    test_result_state=test_result_state,
                    rate=common_params.port_params[(port_index,)].rate,
                    burst_frames=burst_frames,
                )
                ports_result[(port_index,)] = current_port_result
            else:
                current_port_result = ports_result[(port_index,)]
                current_port_result.add_burst_frames(burst_frames)
            if (peer_index,) not in ports_result:
                current_peer_result = PortResult(
                    port_index=peer_index,
                    is_live=is_live,
                    current_packet_size=current_packet_size,
                    iteration=iteration,
                    test_result_state=test_result_state,
                    rate=common_params.port_params[(peer_index,)].rate,
                )
                ports_result[(peer_index,)] = current_peer_result
            else:
                current_peer_result = ports_result[(peer_index,)]
            pt_stream_index = len(tokens)
            pt_stream = tx_port.statistics.tx.obtain_from_stream(stream_id).get()
            current_stream_result.add_tx(len(tokens))
            current_port_result.add_tx(len(tokens))
            tokens.append(pt_stream)

            pr_tpldtraffic_index = len(tokens)
            pr_tpldtraffic = tpld.traffic.get()
            current_stream_result.add_rx(len(tokens))
            current_peer_result.add_rx(len(tokens))
            tokens.append(pr_tpldtraffic)

            pr_tpldlatency = tpld.latency.get()
            current_stream_result.add_la(len(tokens))
            current_peer_result.add_la(len(tokens))
            tokens.append(pr_tpldlatency)

            pr_tpldjitter = tpld.jitter.get()
            current_stream_result.add_ji(len(tokens))
            current_peer_result.add_ji(len(tokens))
            tokens.append(pr_tpldjitter)

            pr_extra = rx_port.statistics.rx.extra.get()
            current_stream_result.add_ex(len(tokens))
            current_peer_result.add_ex(len(tokens))
            tokens.append(pr_extra)

            pr_error = tpld.errors.get()
            current_stream_result.add_rr(len(tokens))

            # tx port should count for rr of its rx port
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


def set_test_state(result_group: ResultGroup, result_state: bool):
    if result_group:
        for i in result_group.all, result_group.port, result_group.stream:
            for v in i.values():
                v.set_result_state(result_state)
