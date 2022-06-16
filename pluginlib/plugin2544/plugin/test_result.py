from decimal import Decimal
from typing import List
from .statistics import (
    FinalStatistic,
    StatisticParams,
    StreamStatistic,
)
from .test_resource import ResourceManager
from ..utils import constants as const


def aggregate_stream_result(resource: "ResourceManager") -> List["StreamStatistic"]:
    res = []
    for port_struct in resource.port_structs:
        for stream_struct in port_struct.stream_structs:
            latency = stream_struct.latency
            jitter = stream_struct.jitter
            res.append(
                StreamStatistic(
                    src_port_id=stream_struct.tx_port.port_identity.name,
                    dest_port_id=stream_struct.rx_port.port_identity.name,
                    src_port_addr=stream_struct.addr_coll.smac,
                    dest_port_addr=stream_struct.addr_coll.dmac,
                    tx_frames=stream_struct.tx_frames.frames,
                    rx_frames=stream_struct.rx_frames.frames,
                    latency_ns_avg=latency.average,
                    latency_ns_min=latency.minimum,
                    latency_ns_max=latency.maximum,
                    jitter_ns_avg=jitter.average,
                    jitter_ns_min=jitter.minimum,
                    jitter_ns_max=jitter.maximum,
                )
            )
    return res


# def aggregate_port_data(resource: "ResourceManager") -> List["PortStatistic"]:
#     res = []
#     for port_struct in resource.port_structs:
#         res.append(
#             PortStatistic(
#                 port_id=port_struct.port_identity.name,
#                 tx_frames=port_struct.statistic.tx_counter.frames,
#                 rx_frames=port_struct.statistic.rx_counter.frames,
#                 tx_rate_l1_bps=port_struct.statistic.tx_counter.l1_bps,
#                 tx_rate_fps=port_struct.statistic.tx_counter.fps,
#                 latency_ns_avg=port_struct.statistic.latency.average,
#                 latency_ns_min=port_struct.statistic.latency.minimum,
#                 latency_ns_max=port_struct.statistic.latency.maximum,
#                 jitter_ns_avg=port_struct.statistic.jitter.average,
#                 jitter_ns_min=port_struct.statistic.jitter.minimum,
#                 jitter_ns_max=port_struct.statistic.jitter.maximum,
#             )
#         )
#     return res


async def aggregate_data(
    resource: "ResourceManager",
    params: StatisticParams,
    is_final: bool = False,
) -> "FinalStatistic":
    await resource.collect(
        params.frame_size,
        params.duration,
        is_final=is_final,
    )
    # port_data = aggregate_port_data(resource)
    return FinalStatistic(
        test_case_type=params.test_case_type,
        is_final=is_final,
        frame_size=params.frame_size,
        repetition=params.repetition,
        tx_rate_percent=params.rate_percent,
        port_data=[port_struct.statistic for port_struct in resource.port_structs],
        # stream_data=aggregate_stream_result(resource),
    )
