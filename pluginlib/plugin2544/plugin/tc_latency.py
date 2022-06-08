from pluginlib.plugin2544.model.m_test_config import TestConfiguration
from pluginlib.plugin2544.model.m_test_type_config import LatencyTest
from pluginlib.plugin2544.plugin.learning import (
    AddressRefreshHandler,
    add_L3_learning_preamble_steps,
    add_flow_based_learning_preamble_steps,
    add_mac_learning_steps,
    schedule_arp_refresh,
)
from pluginlib.plugin2544.plugin.setup_source_port_rates import setup_source_port_rates
from pluginlib.plugin2544.plugin.test_resource import ResourceManager
from pluginlib.plugin2544.utils import constants as const
from pluginlib.plugin2544.utils.field import NonNegativeDecimal


# async def collect_latency_statistics(
#     common_options: "CommonOptions",
#     current_packet_size: NonNegativeDecimal,
#     iteration: int,
#     result_handler: "ResultHandler",
#     xoa_out: "TestSuitPipe",
# ) -> "ResultGroup":
    # average_packet_size = (
    #     sum(test_conf.frame_sizes.packet_size_list)
    #     / len(test_conf.frame_sizes.packet_size_list)
    #     if test_conf.frame_sizes.packet_size_list
    #     else 0
    # )
    # #  statistic jobs
    # port_params = await generate_port_params(stream_lists, rate_percent_dic)
    # stream_params: Dict[Tuple[str, str, int, int], "TestStreamParam"] = {}
    # common_params = TestCommonParam(
    #     TestResultState.PENDING,
    #     Decimal(str(average_packet_size)),
    #     current_packet_size,
    #     iteration,
    #     common_options.actual_duration,
    #     is_live=True,
    #     port_params=port_params,
    #     stream_params=stream_params,
    # )

    # await collect_latency_live_statistics(
    #     stream_lists, result_handler, common_params, state_checker, xoa_out,
    # )
    # await asyncio.sleep(1)
    # return await collect_latency_final_statistics(
    #     stream_lists, result_handler, common_params, xoa_out
    # )


async def run_latency_test(
    resources: "ResourceManager",
    latency_conf: "LatencyTest",
    current_packet_size: NonNegativeDecimal,
    iteration: int,
    result_handler: "ResultHandler",
    address_refresh_handler: "AddressRefreshHandler",
    xoa_out: "TestSuitPipe",
    # throuput_result: Optional[Decimal] = None,
) -> None:
    if not latency_conf.enabled:
        return
    rate_sweep_list = get_rate_sweep_list(latency_conf, throuput_result)

    for rate_percent in rate_sweep_list:
        resources.set_rate(rate_percent)

        await resources.stop_traffic()
        await add_L3_learning_preamble_steps(
            resources,
            current_packet_size,
        )
        await add_mac_learning_steps(
            resources, const.MACLearningMode.EVERYTRIAL
        )  # AddL2TrialLearningSteps
        await add_flow_based_learning_preamble_steps(
            resources,
            current_packet_size,
        )
        await setup_source_port_rates(
            resources,
            current_packet_size,
        )
        await resources.set_tx_time_limit(latency_conf.common_options.actual_duration * 1_000_000)
        await resources.clear_statistic()
        await resources.start_traffic(resources.test_conf.use_port_sync_start)
        await schedule_arp_refresh(resources, address_refresh_handler)
        await collect_latency_statistics(
            stream_lists,
            test_conf,
            latency_conf.common_options,
            current_packet_size,
            iteration,
            rate_percent_dic,
            result_handler,
            state_checker,
            xoa_out,
        )
        await resources.set_tx_time_limit(0)