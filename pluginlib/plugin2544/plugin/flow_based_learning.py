# import asyncio

# from pluginlib.plugin2544.plugin.test_resource import ResourceManager
# from ..utils.field import NonNegativeDecimal

# from .setup_source_port_rates import setup_source_port_rates



# async def add_flow_based_learning_preamble_steps(
#     resources: ResourceManager,
#     current_packet_size: NonNegativeDecimal,
# ) -> None:  # AddFlowBasedLearningPreambleSteps
#     if not resources.test_conf.use_flow_based_learning_preamble:
#         return
#     resources.set_rate(resources.test_conf.learning_rate_pct)
#     await setup_source_port_rates(resources, current_packet_size)
#     await resources.set_frame_limit(resources.test_conf.flow_based_learning_frame_count)
#     await resources.start_traffic()
#     while resources.test_running():
#         await asyncio.gather(
#             *[port_struct.port.traffic.state.get() for port_struct in resources.tx_ports]
#         )
#         await asyncio.sleep(0.1)
#     await asyncio.sleep(resources.test_conf.delay_after_flow_based_learning_ms / 1000)
#     await resources.set_frame_limit(0)  # clear packet limit