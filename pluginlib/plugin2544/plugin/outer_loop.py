from typing import TYPE_CHECKING, Iterator, List, Tuple


from ..utils.field import NonNegativeDecimal
from .statistics import stop_traffic
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
from pluginlib.plugin2544.utils.constants import TestType

if TYPE_CHECKING:
    from ..model import TestConfiguration
    from .structure import PortStruct
    from pluginlib.plugin2544.utils.logger import TestSuitPipe


async def test_run(
    stream_lists: List["StreamInfo"],
    control_ports: List["PortStruct"],
    type_conf: "TypeConf",
    test_conf: "TestConfiguration",
    has_l3: bool,
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    test_case_result: "TestCaseResult",
    xoa_out: "TestSuitPipe",
) -> None:
    result_handler = test_case_result.get_result_handler(type_conf.test_type)
    await stop_traffic(control_ports)
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
            xoa_out,
        )

    elif type_conf.test_type == TestType.LATENCY_JITTER:
        assert isinstance(type_conf, LatencyTest), "Type not matched!"
        throughput_result = test_case_result.get_throughput_result(current_packet_size)
        await run_latency_test(
            stream_lists,
            control_ports,
            test_conf,
            type_conf,
            has_l3,
            current_packet_size,
            iteration,
            result_handler,
            xoa_out,
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
            xoa_out,
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
            xoa_out,
        )


def gen_loop(
    type_conf: "TypeConf",
    test_conf: "TestConfiguration",
    test_case_result: "TestCaseResult",
    xoa_out: "TestSuitPipe",
) -> Iterator[Tuple[int, NonNegativeDecimal]]:
    max_iteration = type_conf.common_options.iterations
    packet_size_list = test_conf.frame_sizes.packet_size_list
    if test_conf.outer_loop_mode.is_iteration:
        for iteration in range(1, max_iteration + 1):
            for current_packet_size in packet_size_list:
                yield iteration, current_packet_size
        result_handler = test_case_result.get_result_handler(type_conf.test_type)
        avg_result(result_handler, max_iteration, type_conf, xoa_out)
    else:
        for current_packet_size in packet_size_list:
            for iteration in range(1, max_iteration + 1):
                yield iteration, current_packet_size
            result_handler = test_case_result.get_result_handler(type_conf.test_type)
            avg_result(
                result_handler, max_iteration, type_conf, xoa_out, current_packet_size
            )


async def setup_for_outer_loop(
    stream_lists: List["StreamInfo"],
    control_ports: List["PortStruct"],
    type_conf: "TypeConf",
    test_conf: "TestConfiguration",
    has_l3: bool,
    test_case_result: "TestCaseResult",
    xoa_out: "TestSuitPipe",
) -> None:
    for iteration, current_packet_size in gen_loop(
        type_conf, test_conf, test_case_result, xoa_out
    ):
        await test_run(
            stream_lists,
            control_ports,
            type_conf,
            test_conf,
            has_l3,
            current_packet_size,
            iteration,
            test_case_result,
            xoa_out,
        )
