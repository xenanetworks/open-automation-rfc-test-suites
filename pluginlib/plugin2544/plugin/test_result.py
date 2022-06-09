from typing import List
from pluginlib.plugin2544.plugin.statistics import (
    LatencyPortStatistic,
    LatencyStatistic,
    LatencyStreamStatistic,
    LatencyTotalStatistic,
)
from pluginlib.plugin2544.plugin.test_resource import ResourceManager


def aggregate_stream_result(resource: "ResourceManager") -> List["LatencyStreamStatistic"]:
    res = []
    for port_struct in resource.port_structs:
        for stream_struct in port_struct.stream_structs:
            latency = stream_struct.latency
            jitter = stream_struct.jitter
            res.append(
                LatencyStreamStatistic(
                    src_port_id=stream_struct.tx_port.port_identity.name,
                    dest_port_id=stream_struct.rx_port.port_identity.name,
                    src_port_addr=stream_struct.addr_coll.smac,
                    dest_port_addr=stream_struct.addr_coll.dmac,
                    tx_frames=stream_struct.tx_frames.frames,
                    rx_frames=stream_struct.rx_frames.frames,
                    latency_ns_avg=latency.avg,
                    latency_ns_min=latency.minimum,
                    latency_ns_max=latency.maximum,
                    jitter_ns_avg=jitter.avg,
                    jitter_ns_min=jitter.minimum,
                    jitter_ns_max=jitter.maximum,
                )
            )
    return res


def aggregate_port_data(resource: "ResourceManager") -> List["LatencyPortStatistic"]:
    res = []
    for port_struct in resource.port_structs:
        res.append(
            LatencyPortStatistic(
                port_id=port_struct.port_identity.name,
                tx_frames=port_struct.statistic.tx_counter.frames,
                rx_frames=port_struct.statistic.rx_counter.frames,
                tx_rate_l1_bps=port_struct.statistic.tx_counter.l1_bps,
                tx_rate_fps=port_struct.statistic.tx_counter.fps,
                latency_ns_avg=port_struct.statistic.latency.average,
                latency_ns_min=port_struct.statistic.latency.minimum,
                latency_ns_max=port_struct.statistic.latency.maximum,
                jitter_ns_avg=port_struct.statistic.jitter.average,
                jitter_ns_min=port_struct.statistic.jitter.minimum,
                jitter_ns_max=port_struct.statistic.jitter.maximum,
            )
        )
    return res


def aggregate_latency_total_data(
    port_statistic: List["LatencyPortStatistic"],
) -> "LatencyTotalStatistic":
    total_tx_frames = 0
    total_rx_frames = 0
    total_tx_rate_l1_bps = 0
    total_tx_rate_fps = 0
    for port_data in port_statistic:
        total_tx_frames += port_data.tx_frames
        total_rx_frames += port_data.rx_frames
        total_tx_rate_l1_bps += port_data.tx_rate_l1_bps
        total_tx_rate_fps += port_data.tx_rate_fps
    return LatencyTotalStatistic(
        tx_frames=total_tx_frames,
        rx_frames=total_rx_frames,
        tx_rate_l1_bps=total_tx_rate_l1_bps,
        tx_rate_fps=total_tx_rate_fps,
    )


def aggregate_latency_data(
    resource: "ResourceManager",
    frame_size,
    repetition,
    rate_percent,
    is_final: bool = False,
) -> "LatencyStatistic":
    port_data = aggregate_port_data(resource)
    total = aggregate_latency_total_data(port_data)
    return LatencyStatistic(
        is_final=is_final,
        frame_size=frame_size,
        repetition=repetition,
        tx_rate_percent=rate_percent,
        port_data=port_data,
        # stream_data=aggregate_stream_result(resource),
        total=total,
    )
