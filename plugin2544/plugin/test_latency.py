import asyncio
import time
from decimal import Decimal
from typing import TYPE_CHECKING, List, Dict, Optional, Tuple
from ..utils.field import NonNegativeDecimal

from ..model import rate_sweep_range
from typing import TYPE_CHECKING, List, Dict


from ..utils.constants import TestResultState
from .common import get_source_port_structs
from .mac_learning import add_L2_trial_learning_steps
from .flow_based_learning import add_flow_based_learning_preamble_steps
from .setup_source_port_rates import setup_source_port_rates
from .statistics import clear_port_stats, set_tx_time_limit, set_traffic_status
from .l3_learning import (
    add_L3_learning_preamble_steps,
    schedule_arp_refresh,
)
from .test_result_structure import (
    BoutEntry,
    TestCommonParam,
    ResultHandler,
    ResultGroup,
    TestStreamParam,
)
from .test_operations import (
    StateChecker,
    generate_port_params,
    should_quit,
    show_result,
    aggregate_test_results,
)


if TYPE_CHECKING:
    from .structure import Structure, StreamInfo
    from ..model import LatencyTest, TestConfiguration, CommonOptions


def get_rate_sweep_list(
    latency_test: "LatencyTest", throughput_result: Optional[Decimal] = None
) -> List[Decimal]:
    if latency_test.use_relative_to_throughput and throughput_result:
        latency_test.rate_sweep_options.set_throughput_relative(throughput_result)
        return rate_sweep_range(latency_test.rate_sweep_options)
    else:
        return latency_test.rate_sweep_list


async def get_latency_result(
    common_params: "TestCommonParam",
    stream_lists: List["StreamInfo"],
    result_handler: "ResultHandler",
) -> "ResultGroup":
    is_live = common_params.is_live
    result_group = await aggregate_test_results(common_params, stream_lists)
    if not is_live:
        result_handler.all_result.extend(list(result_group.all.values()))
        result_handler.port_result.extend(list(result_group.port.values()))
        result_handler.stream_result.extend(list(result_group.stream.values()))
    show_result(result_group, "latency")
    return result_group


async def collect_latency_final_statistics(
    stream_lists: List["StreamInfo"],
    result_handler: "ResultHandler",
    common_params: "TestCommonParam",
) -> ResultGroup:
    common_params.is_live = False
    common_params.test_result_state = TestResultState.PASS

    return await get_latency_result(common_params, stream_lists, result_handler)


async def collect_latency_live_statistics(
    stream_lists: List["StreamInfo"],
    result_handler: "ResultHandler",
    common_params: "TestCommonParam",
    state_checker: "StateChecker",
):
    start_time = time.time()
    while True:
        await get_latency_result(
            common_params,
            stream_lists,
            result_handler,
        )
        if should_quit(state_checker, start_time, common_params.actual_duration):
            break
        await asyncio.sleep(1)


async def collect_latency_statistics(
    stream_lists: List["StreamInfo"],
    test_conf: "TestConfiguration",
    common_options: "CommonOptions",
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    rate_percent_dic: Dict[str, "BoutEntry"],
    result_handler: "ResultHandler",
    state_checker: "StateChecker",
) -> "ResultGroup":
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

    await collect_latency_live_statistics(
        stream_lists, result_handler, common_params, state_checker
    )
    await asyncio.sleep(1)
    return await collect_latency_final_statistics(
        stream_lists, result_handler, common_params
    )


async def run_latency_test(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    test_conf: "TestConfiguration",
    latency_conf: "LatencyTest",
    has_l3: bool,
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    result_handler: "ResultHandler",
    throuput_result: Optional[Decimal] = None,
) -> None:
    if not latency_conf.enabled:
        return
    state_checker = await StateChecker(control_ports, test_conf.should_stop_on_los)
    source_port_structs = get_source_port_structs(control_ports)
    rate_sweep_list = get_rate_sweep_list(latency_conf, throuput_result)

    for k, rate_percent in enumerate(rate_sweep_list):
        rate_percent_dic = {
            port_struct.properties.identity: BoutEntry(
                port_struct.properties.identity, rate=rate_percent
            )
            for port_struct in control_ports
        }

        await set_traffic_status(
            # source_port_structs, test_conf, latency_conf.common_options, False, False
            source_port_structs,
            test_conf,
            False,
        )
        address_refresh_handler = await add_L3_learning_preamble_steps(
            control_ports,
            stream_lists,
            has_l3,
            test_conf,
            # latency_conf.common_options,
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
            latency_conf.common_options,
            current_packet_size,
        )
        await setup_source_port_rates(
            source_port_structs,
            stream_lists,
            test_conf.flow_creation_type,
            # latency_conf.common_options,
            rate_percent_dic,
            current_packet_size,
            # False,
        )
        await set_tx_time_limit(
            source_port_structs, latency_conf.common_options.actual_duration * 1_000_000
        )
        await clear_port_stats(control_ports)
        await set_traffic_status(
            # source_port_structs, test_conf, latency_conf.common_options, True, False
            source_port_structs,
            test_conf,
            True,
        )
        await schedule_arp_refresh(state_checker, address_refresh_handler)
        await collect_latency_statistics(
            stream_lists,
            test_conf,
            latency_conf.common_options,
            current_packet_size,
            iteration,
            rate_percent_dic,
            result_handler,
            state_checker,
        )
