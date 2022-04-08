from typing import TYPE_CHECKING, List
from ..utils.field import NonNegativeDecimal
from .statistics import set_traffic_status
from .stream_base_settings import setup_packet_size
from .structure import StreamInfo, TypeConf
from .test_throughput import run_throughput_test
from .test_back_to_back import run_back_to_back_test
from .test_latency import run_latency_test
from .test_result_structure import TestCaseResult
from .test_operations import avg_result
from .test_frame_loss_rate import run_frame_loss_test
from ..model import LatencyTest
from ..model import BackToBackTest, FrameLossRateTest, LatencyTest, ThroughputTest
from ..utils.constants import TestType

if TYPE_CHECKING:
    from ..model import TestConfiguration
    from .structure import Structure


async def test_run(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    type_conf: "TypeConf",
    test_conf: "TestConfiguration",
    has_l3: bool,
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    test_case_result: "TestCaseResult",
) -> None:
    result_handler = test_case_result.get_result_handler(type_conf.test_type)
    await set_traffic_status(
        control_ports, test_conf, type_conf.common_options, False, False
    )
    await setup_packet_size(control_ports, test_conf.frame_sizes, current_packet_size)

    if type_conf.test_type == TestType.THROUGHPUT:
        assert isinstance(type_conf, ThroughputTest), "Type not matched!"
        await run_throughput_test(
            stream_lists,
            control_ports,
            test_conf,
            type_conf,
            has_l3,
            current_packet_size,
            iteration,
            result_handler,
        )

    elif type_conf.test_type == TestType.LATENCY_JITTER:
        assert isinstance(type_conf, LatencyTest), "Type not matched!"
        throughput_result = test_case_result.get_throughput_result()
        await run_latency_test(
            stream_lists,
            control_ports,
            test_conf,
            type_conf,
            has_l3,
            current_packet_size,
            iteration,
            result_handler,
            throughput_result,
        )

    elif type_conf.test_type == TestType.FRAME_LOSS_RATE:
        assert isinstance(type_conf, FrameLossRateTest), "Type not matched!"
        await run_frame_loss_test(
            stream_lists,
            control_ports,
            test_conf,
            type_conf,
            has_l3,
            current_packet_size,
            iteration,
            result_handler,
        )
    elif type_conf.test_type == TestType.BACK_TO_BACK:
        assert isinstance(type_conf, BackToBackTest), "Type not matched!"
        await run_back_to_back_test(
            stream_lists,
            control_ports,
            test_conf,
            type_conf,
            has_l3,
            current_packet_size,
            iteration,
            result_handler,
        )


async def _setup_for_outer_loop_iterations(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    type_conf: "TypeConf",
    test_conf: "TestConfiguration",
    has_l3: bool,
    test_case_result: "TestCaseResult",
) -> None:  # SetupForOuterLoopPacketSizes
    max_iteration = type_conf.common_options.iterations
    for iteration in range(1, max_iteration + 1):
        for current_packet_size in test_conf.frame_sizes.packet_size_list:
            await test_run(
                stream_lists,
                control_ports,
                type_conf,
                test_conf,
                has_l3,
                current_packet_size,
                iteration,
                test_case_result,
            )
    result_handler = test_case_result.get_result_handler(type_conf.test_type)
    avg_result(result_handler, max_iteration, type_conf)


async def _setup_for_outer_loop_packet_sizes(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    type_conf: "TypeConf",
    test_conf: "TestConfiguration",
    has_l3: bool,
    test_case_result: "TestCaseResult",
) -> None:  # SetupForOuterLoopIterations
    max_iteration = type_conf.common_options.iterations
    for current_packet_size in test_conf.frame_sizes.packet_size_list:
        for iteration in range(1, max_iteration + 1):
            await test_run(
                stream_lists,
                control_ports,
                type_conf,
                test_conf,
                has_l3,
                current_packet_size,
                iteration,
                test_case_result,
            )
        result_handler = test_case_result.get_result_handler(type_conf.test_type)
        avg_result(result_handler, max_iteration, type_conf, current_packet_size)


async def setup_for_outer_loop(
    stream_lists: List["StreamInfo"],
    control_ports: List["Structure"],
    type_conf: "TypeConf",
    test_conf: "TestConfiguration",
    has_l3: bool,
    test_case_result: "TestCaseResult",
) -> None:
    if test_conf.outer_loop_mode.is_iteration:
        await _setup_for_outer_loop_iterations(
            stream_lists,
            control_ports,
            type_conf,
            test_conf,
            has_l3,
            test_case_result,
        )
    else:
        await _setup_for_outer_loop_packet_sizes(
            stream_lists,
            control_ports,
            type_conf,
            test_conf,
            has_l3,
            test_case_result,
        )
