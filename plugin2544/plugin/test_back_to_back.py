import asyncio
from dataclasses import dataclass
from decimal import Decimal
import math
from time import time
from typing import TYPE_CHECKING, List, Dict, Optional, Tuple
from ..utils.field import NonNegativeDecimal
from ..utils.constants import TestResultState, TestType

# from ..utils.scheduler import schedule
from .common import get_source_port_structs
from .mac_learning import add_L2_trial_learning_steps
from .flow_based_learning import add_flow_based_learning_preamble_steps
from .statistics import (
    clear_port_stats,
    set_tx_time_limit,
    set_traffic_status,
    stop_traffic,
)
from .l3_learning import (
    AddressRefreshHandler,
    schedule_arp_refresh,
    add_L3_learning_preamble_steps,
)
from .test_result_structure import (
    BoutEntry,
    IterationEntry,
    TestCommonParam,
    ResultHandler,
    ResultGroup,
    TestStreamParam,
)
from .test_operations import (
    StateChecker,
    generate_port_params,
    get_port_rate,
    get_use_port_speed,
    should_quit,
    show_result,
    aggregate_test_results,
    set_test_state,
)
from xoa_driver.utils import apply

if TYPE_CHECKING:
    from .structure import Structure, StreamInfo
    from ..model import BackToBackTest, TestConfiguration, CommonOptions


@dataclass
class BackToBackBoutEntry(BoutEntry):
    left_bound: Decimal = Decimal("0")
    right_bound: Decimal = Decimal("0")
    last_move: int = 0
    rate: Decimal = Decimal("0")


def goto_next(boundaries: Dict[str, "IterationEntry"]) -> Dict[str, "IterationEntry"]:
    for port_index, boundary in boundaries.copy().items():
        boundary.current = boundary.next

    return boundaries


async def get_initial_boundaries(
    back_to_back_conf: "BackToBackTest",
    source_port_structs: List["Structure"],
    rate_percent_dic: Dict[str, "BackToBackBoutEntry"],
    current_packet_size: NonNegativeDecimal,
) -> Dict[str, "BackToBackBoutEntry"]:
    result = {}
    for port_struct in source_port_structs:
        rate = get_port_rate(port_struct, rate_percent_dic)
        port_speed = await get_use_port_speed(port_struct)
        max_value = (
            Decimal(str(back_to_back_conf.common_options.actual_duration))
            * Decimal(rate)
            / Decimal("100")
            * Decimal(str(port_speed))
            / (
                Decimal("8")
                * (
                    Decimal(str(current_packet_size))
                    + Decimal(str(port_struct.port_conf.inter_frame_gap))
                )
            )
        )
        # else:
        #     max_value = (
        #         Decimal(str(back_to_back_conf.common_options.actual_frames))
        #         * Decimal(str(rate))
        #         / Decimal("100")
        #     )
        result[port_struct.properties.identity] = BackToBackBoutEntry(
            current=max_value,
            next=max_value,
            left_bound=Decimal("0"),
            right_bound=max_value,
            rate=rate,
        )
    return result


async def run_back_to_back_test(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    test_conf: "TestConfiguration",
    back_to_back_conf: "BackToBackTest",
    has_l3: bool,
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    result_handler: "ResultHandler",
) -> None:
    if not back_to_back_conf.enabled:
        return
    state_checker = await StateChecker(control_ports, test_conf.should_stop_on_los)
    source_port_structs = get_source_port_structs(control_ports)
    address_refresh_handler = await add_L3_learning_preamble_steps(
        control_ports,
        stream_lists,
        has_l3,
        test_conf,
        current_packet_size,
        state_checker,
    )
    await add_L2_trial_learning_steps(
        control_ports,
        test_conf.mac_learning_mode,
        test_conf.mac_learning_frame_count,
    )  # AddL2TrialLearningSteps
    await add_flow_based_learning_preamble_steps(
        stream_lists,
        source_port_structs,
        test_conf,
        current_packet_size,
        state_checker,
    )

    await back_to_back_sweep(
        stream_lists,
        control_ports,
        test_conf,
        back_to_back_conf,
        current_packet_size,
        iteration,
        result_handler,
        source_port_structs,
        address_refresh_handler,
        state_checker,
    )


async def back_to_back_sweep(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    test_conf: "TestConfiguration",
    back_to_back_conf: "BackToBackTest",
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    result_handler: "ResultHandler",
    source_port_structs: List["Structure"],
    address_refresh_handler: Optional["AddressRefreshHandler"],
    state_checker: "StateChecker",
):
    rate_sweep_list = back_to_back_conf.rate_sweep_list
    for k, rate_percent in enumerate(rate_sweep_list):
        rate_percent_dic = {
            port_struct.properties.identity: BackToBackBoutEntry(
                port_struct.properties.identity, rate=rate_percent
            )
            for port_struct in control_ports
        }
        await schedule_arp_refresh(state_checker, address_refresh_handler)
        await back_to_back_binary_search(
            stream_lists,
            control_ports,
            test_conf,
            back_to_back_conf,
            current_packet_size,
            iteration,
            result_handler,
            source_port_structs,
            address_refresh_handler,
            rate_percent_dic,
            state_checker,
        )


async def setup_source_port_burst_for_streams(
    stream_lists: List["StreamInfo"],
    source_port_structs: List["Structure"],
    rate_percent_dic: Dict[str, IterationEntry],
    current_packet_size: NonNegativeDecimal,
    boundaries: Dict[str, "BackToBackBoutEntry"],
    is_stream_based: bool,
) -> Dict[Tuple[str, str, int, int], TestStreamParam]:
    tokens = []
    burst_frame_dic = {}
    if not is_stream_based:
        return {}
    for port_struct in source_port_structs:
        src_port_speed = await get_use_port_speed(port_struct)
        dest_port_list = port_struct.properties.peers
        inter_frame_gap = port_struct.port_conf.inter_frame_gap
        total_frame_count = boundaries[port_struct.properties.identity].current
        rate_percent = get_port_rate(port_struct, rate_percent_dic)

        for peer_struct in dest_port_list:
            stream_info_list = [
                stream_info
                for stream_info in stream_lists
                if stream_info.port_struct == port_struct
                and stream_info.peer_struct == peer_struct
            ]
            port_stream_count = len(dest_port_list) * len(stream_info_list)
            stream_burst = Decimal(str(total_frame_count)) / Decimal(
                str(port_stream_count)
            )
            stream_rate_percent = Decimal(str(rate_percent)) / Decimal(
                str(port_stream_count)
            )
            stream_rate_bps_L1 = (
                Decimal(str(stream_rate_percent))
                * Decimal(str(src_port_speed))
                / Decimal("100")
            )
            stream_rate_bps_L2 = math.floor(
                Decimal(str(stream_rate_bps_L1))
                * Decimal(str(current_packet_size))
                / (Decimal(str(current_packet_size)) + Decimal(str(inter_frame_gap)))
            )
            for stream_info in stream_info_list:
                stream = port_struct.port.streams.obtain(stream_info.stream_id)
                tokens.append(stream.rate.l2bps.set(stream_rate_bps_L2))
                tokens += [stream.packet.limit.set(math.floor(stream_burst))]
                burst_frame_dic[
                    (
                        stream_info.port_struct.properties.identity,
                        stream_info.peer_struct.properties.identity,
                        stream_info.stream_id,
                        stream_info.tpldid,
                    )
                ] = TestStreamParam(stream_burst)

    await apply(*tokens)
    return burst_frame_dic


async def back_to_back_binary_search(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    test_conf: "TestConfiguration",
    back_to_back_conf: "BackToBackTest",
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    result_handler: "ResultHandler",
    source_port_structs: List["Structure"],
    address_refresh_handler: Optional["AddressRefreshHandler"],
    rate_percent_dic: Dict[str, BackToBackBoutEntry],
    state_checker: "StateChecker",
):
    result_group = None
    boundaries = await get_initial_boundaries(
        back_to_back_conf,
        source_port_structs,
        rate_percent_dic,
        current_packet_size,
    )
    is_stream_based = test_conf.flow_creation_type.is_stream_based

    while True:
        await stop_traffic(source_port_structs)
        should_continue, test_passed = check_boundaries(
            result_group, boundaries, back_to_back_conf
        )

        if result_group:
            set_test_state(result_group, test_passed)
            show_result(result_group, TestType.BACK_TO_BACK)
        if not should_continue:
            break
        boundaries = goto_next(boundaries)
        burst_frame_dic = await setup_source_port_burst_for_streams(
            stream_lists,
            source_port_structs,
            rate_percent_dic,
            current_packet_size,
            boundaries,
            is_stream_based,
        )
        await set_tx_time_limit(
            source_port_structs,
            back_to_back_conf.common_options.actual_duration * 1_000_000,
        )
        await clear_port_stats(control_ports)
        await set_traffic_status(
            source_port_structs,
            test_conf,
            True,
        )
        await schedule_arp_refresh(state_checker, address_refresh_handler)
        result_group = await collect_back_to_back_statistics(
            stream_lists,
            test_conf,
            back_to_back_conf.common_options,
            current_packet_size,
            iteration,
            rate_percent_dic,
            result_handler,
            burst_frame_dic,
            state_checker,
        )


async def collect_back_to_back_statistics(
    stream_lists: List["StreamInfo"],
    test_conf: "TestConfiguration",
    common_options: "CommonOptions",
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    rate_percent_dic: Dict[str, "BackToBackBoutEntry"],
    result_handler: "ResultHandler",
    burst_frame_dic: Dict[Tuple[str, str, int, int], TestStreamParam],
    state_checker: "StateChecker",
) -> ResultGroup:
    average_packet_size = (
        sum(test_conf.frame_sizes.packet_size_list)
        / len(test_conf.frame_sizes.packet_size_list)
        if test_conf.frame_sizes.packet_size_list
        else 0
    )
    #  statistic jobs
    port_params = await generate_port_params(stream_lists, rate_percent_dic)
    common_params = TestCommonParam(
        TestResultState.PENDING,
        Decimal(str(average_packet_size)),
        current_packet_size,
        iteration,
        common_options.actual_duration,
        is_live=True,
        port_params=port_params,
        stream_params=burst_frame_dic,
    )
    await collect_back_to_back_live_statistics(
        state_checker, stream_lists, common_params, result_handler
    )
    return await collect_back_to_back_final_statistics(
        stream_lists, common_params, result_handler
    )


async def get_back_to_back_result(
    common_params: "TestCommonParam",
    stream_lists: List["StreamInfo"],
    result_handler: "ResultHandler",
):
    result_group = await aggregate_test_results(common_params, stream_lists)
    is_live = common_params.is_live

    if not is_live:
        result_handler.all_result.extend(list(result_group.all.values()))
        result_handler.port_result.extend(list(result_group.port.values()))
        result_handler.stream_result.extend(list(result_group.stream.values()))
    show_result(result_group, TestType.BACK_TO_BACK)
    return result_group


async def collect_back_to_back_live_statistics(
    state_checker: "StateChecker",
    stream_lists: List["StreamInfo"],
    common_params: "TestCommonParam",
    result_handler: "ResultHandler",
) -> None:
    start_time = time()
    while True:
        await get_back_to_back_result(common_params, stream_lists, result_handler)
        if should_quit(state_checker, start_time, common_params.actual_duration):
            break
        await asyncio.sleep(1)


async def collect_back_to_back_final_statistics(
    stream_lists: List["StreamInfo"],
    common_params: "TestCommonParam",
    result_handler: "ResultHandler",
) -> ResultGroup:
    common_params.is_live = False
    await asyncio.sleep(1)
    return await get_back_to_back_result(common_params, stream_lists, result_handler)


def check_boundaries(
    result_group: Optional["ResultGroup"],
    boundaries: Dict[str, "BackToBackBoutEntry"],
    back_to_back_conf: "BackToBackTest",
):
    if result_group is None:
        return True, False
    bool_result = []

    for port_index_or_all, boundary in boundaries.items():
        port_should_continue, port_test_passed = False, False
        if boundary.left_bound > boundary.right_bound:
            port_should_continue, port_test_passed = False, False
        else:
            cur_result_data = result_group.port[(port_index_or_all,)]
            res = Decimal(str(back_to_back_conf.rate_sweep_options.burst_resolution))
            if cur_result_data.loss_ratio_pct == Decimal("0"):
                update_left_bound(boundary)
            else:
                update_right_bound(boundary)
            if compare_search_pointer(boundary, res):
                port_should_continue = False
                port_test_passed = True
            else:
                port_should_continue = True
        bool_result.append((port_should_continue, port_test_passed))
    return (
        any(i[0] for i in bool_result),
        all(i[1] for i in bool_result),
    )


def update_left_bound(boundary: "BackToBackBoutEntry") -> None:
    boundary.left_bound = boundary.current
    boundary.next = (
        Decimal(str(boundary.left_bound)) + Decimal(str(boundary.right_bound))
    ) / 2

    boundary.last_move = -1


def update_right_bound(boundary: "BackToBackBoutEntry") -> None:
    boundary.right_bound = boundary.current
    boundary.next = (
        Decimal(str(boundary.left_bound)) + Decimal(str(boundary.right_bound))
    ) / 2

    boundary.last_move = 1


def compare_search_pointer(boundary: "BackToBackBoutEntry", res: Decimal) -> bool:
    if abs(boundary.next - boundary.current) <= res:
        if boundary.next >= boundary.current:
            # make sure we report the right boundary if we are so close to it.
            if (boundary.right_bound - boundary.current) <= res:
                boundary.current = boundary.right_bound
        else:
            if (boundary.current - boundary.left_bound) <= res:
                boundary.current = boundary.left_bound
        return True
    else:
        return False
