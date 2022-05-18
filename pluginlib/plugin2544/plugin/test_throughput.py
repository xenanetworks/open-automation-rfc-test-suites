import asyncio
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from time import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple


from ..utils.field import NonNegativeDecimal
from ..utils.constants import TestResultState, TestType

from .common import filter_port_structs
from .flow_based_learning import add_flow_based_learning_preamble_steps
from .l3_learning import (
    AddressRefreshHandler,
    schedule_arp_refresh,
    add_L3_learning_preamble_steps,
)

from .mac_learning import add_L2_trial_learning_steps
from .setup_source_port_rates import setup_source_port_rates
from .statistics import clear_port_stats, set_port_txtime_limit, set_traffic_status
from .test_result_structure import (
    AllResult,
    BoutEntry,
    ResultGroup,
    TestCommonParam,
    ResultHandler,
    TestStreamParam,
)
from .test_operations import (
    StateChecker,
    generate_port_params,
    aggregate_test_results,
    should_quit,
    show_result,
    set_test_state,
)

if TYPE_CHECKING:
    from ..model import CommonOptions, TestConfiguration
    from .structure import StreamInfo, Structure
    from ..model import ThroughputTest
    from pluginlib.plugin2544.utils.logger import TestSuitPipe

@dataclass
class ThroughputBoutEntry(BoutEntry):
    best_result: Optional[ResultGroup] = None
    left_bound: Decimal = Decimal("0")
    right_bound: Decimal = Decimal("0")
    last_move: int = 0

    def copy(self) -> "ThroughputBoutEntry":
        return deepcopy(self)


async def show_throughput_result(
    common_params: "TestCommonParam",
    stream_lists: List["StreamInfo"],
    xoa_out: "TestSuitPipe",
) -> "ResultGroup":
    result_group = await aggregate_test_results(common_params, stream_lists)
    show_result(result_group, TestType.THROUGHPUT, xoa_out)
    return result_group


def get_initial_boundaries(
    throughput_conf: "ThroughputTest", source_port_structs: List["Structure"]
) -> Dict[str, "ThroughputBoutEntry"]:
    one = ThroughputBoutEntry(
        current=Decimal(str(throughput_conf.rate_iteration_options.initial_value_pct)),
        next=Decimal(str(throughput_conf.rate_iteration_options.initial_value_pct)),
        left_bound=Decimal(
            str(throughput_conf.rate_iteration_options.minimum_value_pct)
        ),
        right_bound=Decimal(
            str(throughput_conf.rate_iteration_options.maximum_value_pct)
        ),
        rate=Decimal(str(throughput_conf.rate_iteration_options.initial_value_pct)),
    )
    result = {}
    if throughput_conf.rate_iteration_options.result_scope.is_per_source_port:
        for i in source_port_structs:
            ele = one.copy()
            ele.port_index = i.properties.identity
            result[i.properties.identity] = ele
    else:
        result["all"] = one
    return result


def update_left_bound(
    boundary: "ThroughputBoutEntry", is_fast: bool, loss_ratio: Decimal, res: Decimal
) -> None:
    boundary.left_bound = boundary.current
    boundary.last_move = -1
    if abs(
        (Decimal(str(boundary.left_bound)) + Decimal(str(boundary.right_bound))) / 2
        - Decimal(str(boundary.left_bound))
    ) < Decimal(str(res)):
        boundary.next = boundary.right_bound
        boundary.left_bound = boundary.right_bound
    else:
        boundary.next = (
            Decimal(str(boundary.left_bound)) + Decimal(str(boundary.right_bound))
        ) / 2


def update_right_bound(
    boundary: "ThroughputBoutEntry", is_fast: bool, loss_ratio: Decimal, res: Decimal
) -> None:
    boundary.right_bound = boundary.current
    boundary.last_move = 1

    if abs(
        (Decimal(str(boundary.left_bound)) + Decimal(str(boundary.right_bound))) / 2
        - Decimal(str(boundary.right_bound))
    ) < Decimal(str(res)):
        boundary.next = boundary.left_bound
        boundary.right_bound = boundary.left_bound
    if is_fast:
        boundary.next = max(
            Decimal(str(boundary.current))
            * (Decimal("1.0") - Decimal(str(loss_ratio))),
            Decimal(str(boundary.left_bound)),
        )
    else:
        boundary.next = (
            Decimal(str(boundary.left_bound)) + Decimal(str(boundary.right_bound))
        ) / 2


def compare_search_pointer(boundary: "ThroughputBoutEntry") -> bool:
    return boundary.next == boundary.current


def pass_threshold(
    cur_result_data: "ThroughputBoutEntry", throughput_conf: "ThroughputTest"
) -> bool:
    return (
        cur_result_data.current >= throughput_conf.pass_threshold_pct
        if throughput_conf.use_pass_threshold
        else True
    )


def check_boundaries(
    result_group: Optional["ResultGroup"],
    boundaries: Dict[str, "ThroughputBoutEntry"],
    throughput_conf: "ThroughputTest",
) -> Tuple[bool, bool]:
    if result_group is None:
        return True, False
    bool_result = []

    for port_index_or_all, boundary in boundaries.items():
        port_should_continue, port_test_passed = False, False
        if boundary.left_bound > boundary.right_bound:
            port_should_continue, port_test_passed = False, False
        else:
            cur_result_data = (
                result_group.port[(port_index_or_all,)]
                if throughput_conf.rate_iteration_options.result_scope.is_per_source_port
                else result_group.all[(port_index_or_all,)]
            )
            is_fast = throughput_conf.rate_iteration_options.search_type.is_fast
            res = Decimal(
                str(throughput_conf.rate_iteration_options.value_resolution_pct)
            )
            if cur_result_data.loss_ratio_pct <= throughput_conf.acceptable_loss_pct:
                boundary.best_result = result_group
                update_left_bound(boundary, is_fast, cur_result_data.loss_ratio, res)
            else:
                update_right_bound(boundary, is_fast, cur_result_data.loss_ratio, res)
            if compare_search_pointer(boundary):
                port_test_passed = pass_threshold(boundary, throughput_conf)
                port_should_continue = False
            else:
                port_should_continue = True
        bool_result.append((port_should_continue, port_test_passed))
    return (
        any(i[0] for i in bool_result),
        all(i[1] for i in bool_result),
    )


def goto_next_percent(
    boundaries: Dict[str, "ThroughputBoutEntry"]
) -> Dict[str, "ThroughputBoutEntry"]:
    for port_index, boundary in boundaries.copy().items():
        boundary.current = boundary.next
        boundary.rate = boundary.next

    return boundaries


async def collect_throughput_live_statistics(
    state_checker: "StateChecker",
    stream_lists: List["StreamInfo"],
    common_params: "TestCommonParam",
    xoa_out: "TestSuitPipe",
) -> None:
    start_time = time()
    while True:
        await show_throughput_result(common_params, stream_lists, xoa_out)
        if should_quit(state_checker, start_time, common_params.actual_duration):
            break
        await asyncio.sleep(1)


async def throughput_statistic_collect(
    stream_lists: List["StreamInfo"],
    test_conf: "TestConfiguration",
    common_options: "CommonOptions",
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    rate_percent_dic: Dict[str, "ThroughputBoutEntry"],
    state_checker: "StateChecker",
    xoa_out: "TestSuitPipe",
) -> ResultGroup:
    average_packet_size = (
        sum(test_conf.frame_sizes.packet_size_list)
        / len(test_conf.frame_sizes.packet_size_list)
        if test_conf.frame_sizes.packet_size_list
        else 0
    )
    #  statistic jobs
    port_params = await generate_port_params(stream_lists, rate_percent_dic)
    stream_params: Dict[Tuple[str, str, int, int], "TestStreamParam"] = {}
    common_params = TestCommonParam(
        TestResultState.PENDING,
        Decimal(str(average_packet_size)),
        current_packet_size,
        iteration,
        common_options.actual_duration,
        is_live=True,
        port_params=port_params,
        stream_params=stream_params,
    )
    await collect_throughput_live_statistics(state_checker, stream_lists, common_params, xoa_out)
    common_params.is_live = False
    await asyncio.sleep(1)
    return await show_throughput_result(common_params, stream_lists, xoa_out)


async def run_throughput_test(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    test_conf: "TestConfiguration",
    throughput_conf: "ThroughputTest",
    has_l3: bool,
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    result_handler: "ResultHandler",
    xoa_out: "TestSuitPipe",
) -> None:
    if not throughput_conf.enabled:
        return
    state_checker = await StateChecker(control_ports, test_conf.should_stop_on_los)
    source_port_structs = filter_port_structs(control_ports)
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
    await throughput_binary_search(
        stream_lists,
        control_ports,
        test_conf,
        throughput_conf,
        current_packet_size,
        iteration,
        result_handler,
        source_port_structs,
        address_refresh_handler,
        state_checker,
        xoa_out,
    )


async def throughput_binary_search(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    test_conf: "TestConfiguration",
    throughput_conf: "ThroughputTest",
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    result_handler: "ResultHandler",
    source_port_structs: List["Structure"],
    address_refresh_handler: Optional["AddressRefreshHandler"],
    state_checker: "StateChecker",
    xoa_out: "TestSuitPipe",
) -> Optional["ResultGroup"]:

    boundaries = get_initial_boundaries(throughput_conf, source_port_structs)
    result_group = None
    while True:
        should_continue, test_passed = check_boundaries(
            result_group, boundaries, throughput_conf
        )
        if result_group:
            show_result(result_group, TestType.THROUGHPUT, xoa_out)
        if not should_continue:
            break
        rate_percent_dic = goto_next_percent(boundaries)
        await setup_source_port_rates(
            source_port_structs,
            stream_lists,
            test_conf.flow_creation_type,
            rate_percent_dic,
            current_packet_size,
        )
        await set_port_txtime_limit(
            source_port_structs,
            throughput_conf.common_options.actual_duration * 1_000_000,
        )
        await clear_port_stats(control_ports)
        await set_traffic_status(
            source_port_structs,
            test_conf,
            True,
        )
        await schedule_arp_refresh(state_checker, address_refresh_handler)
        result_group = await throughput_statistic_collect(
            stream_lists,
            test_conf,
            throughput_conf.common_options,
            current_packet_size,
            iteration,
            rate_percent_dic,
            state_checker,
            xoa_out,
        )
        await set_port_txtime_limit(
            source_port_structs,
            Decimal(0),
        )
    return use_best_result(boundaries, throughput_conf, test_passed, result_handler, xoa_out)


def use_best_src_port_result(
    boundaries: Dict[str, "ThroughputBoutEntry"], test_passed: bool
) -> "ResultGroup":
    stream_result_dic = {}
    port_result_dic = {}
    all_result_dic = {}
    for k, v in boundaries.items():
        if not v.best_result:
            continue
        for sk, sr in v.best_result.stream.copy().items():
            sr.set_result_state(test_passed)
            stream_result_dic[sk] = sr
        co = v.best_result.port.copy()
        for pk, pr in co.items():
            pr.set_result_state(test_passed)
            port_result_dic[pk] = pr

    all_result = AllResult()
    all_result.read_from_ports(*port_result_dic.values())
    all_result_dic = {("all",): all_result}
    final_result_group = ResultGroup(
        stream=stream_result_dic, port=port_result_dic, all=all_result_dic
    )
    return final_result_group


def use_best_common_result(
    boundaries: Dict[str, "ThroughputBoutEntry"], test_passed: bool
) -> Optional["ResultGroup"]:
    final_result = boundaries["all"].best_result
    if not final_result:
        return None
    set_test_state(final_result, test_passed)
    return final_result


def use_best_result(
    boundaries: Dict[str, "ThroughputBoutEntry"],
    throughput_conf: "ThroughputTest",
    test_passed: bool,
    result_handler: "ResultHandler",
    xoa_out: "TestSuitPipe",
) -> Optional["ResultGroup"]:
    final_result = None
    if throughput_conf.rate_iteration_options.result_scope.is_per_source_port:
        final_result = use_best_src_port_result(boundaries, test_passed)
    else:
        final_result = use_best_common_result(boundaries, test_passed)
    if final_result:
        result_handler.all_result.extend(list(final_result.all.values()))
        result_handler.port_result.extend(list(final_result.port.values()))
        result_handler.stream_result.extend(list(final_result.stream.values()))
        show_result(final_result, TestType.THROUGHPUT, xoa_out)
    return final_result
