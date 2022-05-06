import asyncio
from decimal import Decimal
from time import time
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from pydantic import NonNegativeInt
from ..utils.field import NonNegativeDecimal

from .statistics import (
    clear_port_stats,
    set_tx_time_limit,
    set_traffic_status,
)
from ..utils.constants import TestResultState, TestType
from .common import get_source_port_structs
from .flow_based_learning import add_flow_based_learning_preamble_steps
from .l3_learning import schedule_arp_refresh, add_L3_learning_preamble_steps
from .mac_learning import add_L2_trial_learning_steps
from .setup_source_port_rates import setup_source_port_rates
from .test_result_structure import (
    BoutEntry,
    ResultGroup,
    TestCommonParam,
    ResultHandler,
    TestStreamParam,
)
from .test_operations import (
    StateChecker,
    check_if_frame_loss_success,
    generate_port_params,
    should_quit,
    show_result,
    aggregate_test_results,
)
from xoa_driver.utils import apply

if TYPE_CHECKING:
    from ..model import TestConfiguration
    from .structure import StreamInfo, Structure
    from ..model import FrameLossRateTest


async def get_frame_loss_result(
    common_params: TestCommonParam,
    stream_lists: List["StreamInfo"],
    result_handler: ResultHandler,
    frame_loss_conf: Optional["FrameLossRateTest"] = None,
) -> ResultGroup:
    result_group = await aggregate_test_results(common_params, stream_lists)
    is_live = common_params.is_live
    if not is_live and frame_loss_conf:
        for i in result_group.all, result_group.port, result_group.stream:
            for final_result in i.values():
                check_if_frame_loss_success(frame_loss_conf, final_result)
        result_handler.all_result.extend(list(result_group.all.values()))
        result_handler.port_result.extend(list(result_group.port.values()))
        result_handler.stream_result.extend(list(result_group.stream.values()))
    show_result(result_group, TestType.FRAME_LOSS_RATE)
    return result_group


async def collect_frame_loss_live_statistics(
    stream_lists: List["StreamInfo"],
    state_checker: "StateChecker",
    result_handler: ResultHandler,
    common_params: TestCommonParam,
):
    start_time = time()
    while True:
        await get_frame_loss_result(common_params, stream_lists, result_handler)
        if should_quit(state_checker, start_time, common_params.actual_duration):
            break
        await asyncio.sleep(1)


async def collect_frame_loss_final_statistics(
    stream_lists: List["StreamInfo"],
    result_handler: "ResultHandler",
    common_params: "TestCommonParam",
    frame_loss_conf: "FrameLossRateTest",
) -> ResultGroup:
    common_params.is_live = False
    await asyncio.sleep(1)
    return await get_frame_loss_result(
        common_params, stream_lists, result_handler, frame_loss_conf
    )


async def collect_frame_loss_statistics(
    stream_lists: List["StreamInfo"],
    test_conf: "TestConfiguration",
    frame_loss_conf: "FrameLossRateTest",
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    rate_percent_dic: Dict[str, BoutEntry],
    result_handler: ResultHandler,
    state_checker: "StateChecker",
) -> None:
    average_packet_size = (
        sum(test_conf.frame_sizes.packet_size_list)
        / len(test_conf.frame_sizes.packet_size_list)
        if test_conf.frame_sizes.packet_size_list
        else 0
    )
    port_params = await generate_port_params(stream_lists, rate_percent_dic)
    stream_params: Dict[Tuple[str, str, int, int], "TestStreamParam"] = {}

    common_params = TestCommonParam(
        TestResultState.PENDING,
        Decimal(str(average_packet_size)),
        current_packet_size,
        iteration,
        frame_loss_conf.common_options.actual_duration,
        is_live=True,
        port_params=port_params,
        stream_params=stream_params,
    )
    await collect_frame_loss_live_statistics(
        stream_lists,
        state_checker,
        result_handler,
        common_params,
    )
    await collect_frame_loss_final_statistics(
        stream_lists, result_handler, common_params, frame_loss_conf
    )


async def set_gap_monitor(
    source_port_structs: List["Structure"],
    use_gap_monitor: bool,
    gap_monitor_start_microsec: NonNegativeInt,
    gap_monitor_stop_frames: NonNegativeInt,
) -> None:
    if use_gap_monitor:
        tokens = []
        for port_struct in source_port_structs:
            tokens.append(
                port_struct.port.gap_monitor.set(
                    gap_monitor_start_microsec, gap_monitor_stop_frames
                )
            )
        await apply(*tokens)


async def run_frame_loss_test(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    test_conf: "TestConfiguration",
    frame_loss_conf: "FrameLossRateTest",
    has_l3: bool,
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    result_handler: ResultHandler,
) -> None:
    if not frame_loss_conf.enabled:
        return
    state_checker = await StateChecker(control_ports, test_conf.should_stop_on_los)
    source_port_structs = get_source_port_structs(control_ports)
    rate_sweep_list = frame_loss_conf.rate_sweep_list
    for rate_percent in rate_sweep_list:
        rate_percent_dic = {
            port_struct.properties.identity: BoutEntry(
                port_struct.properties.identity, rate_percent
            )
            for port_struct in control_ports
        }
        await set_traffic_status(
            source_port_structs,
            test_conf,
            False,
        )
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
        )
        await setup_source_port_rates(
            source_port_structs,
            stream_lists,
            test_conf.flow_creation_type,
            rate_percent_dic,
            current_packet_size,
        )
        await set_tx_time_limit(
            source_port_structs,
            frame_loss_conf.common_options.actual_duration * 1_000_000,
        )
        await clear_port_stats(control_ports)
        await set_traffic_status(
            source_port_structs,
            test_conf,
            True,
        )
        await schedule_arp_refresh(state_checker, address_refresh_handler)
        await collect_frame_loss_statistics(
            stream_lists,
            test_conf,
            frame_loss_conf,
            current_packet_size,
            iteration,
            rate_percent_dic,
            result_handler,
            state_checker,
        )
