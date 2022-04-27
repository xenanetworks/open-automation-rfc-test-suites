from typing import Dict, Tuple, TYPE_CHECKING
from ..utils.logger import logger

if TYPE_CHECKING:
    from .test_result_structure import PortResult, AllResult


def show_all_throughput_result(all_result: Dict[Tuple, "AllResult"]) -> None:
    logger.error("")
    logger.error("")
    for k, v in all_result.items():
        if not v.is_live:
            if v.test_result_state.value != "pending":
                logger.error("#" * 100)
            else:
                logger.error("=" * 100)
        logger.error(
            "Throughput: "
            + f"All Results -- final: {not v.is_live} "
            + f"{k}: Frame Size: {v.current_packet_size} "
            + f"Result State: {v.test_result_state} "
            + f"Iter.#: {v.iteration} "
            + (f"Tx Off Rate(Percent): {v.rate} " if v.is_common else "")
            + (f"Tx Act. Rate(Percent): {v.actual_rate} " if not v.is_common else "")
            + f"Tx(Frames): {float(v.tx_frames)} "
            + f"Tx Rate(L1)(Bits): {float(v.tx_rate_l1)} "
            + f"Tx Rate(L2)(Bits): {float(v.tx_rate_l2)} "
            + f"Tx Rate(Fps): {float(v.tx_fps)} "
            + f"Rx(Frames): {float(v.rx_frames)} "
            + f"Loss(Frames): {float(v.loss_frames)} "
            + f"Loss Rate(Percent): {float(v.loss_ratio_pct)}% "
            + f"BER(est): {float(v.ber)} "
            + f"FCS Errors(Frames): {float(v.fcs_error)}% "
        )


def show_port_throughput_result(port_result: Dict[Tuple, "PortResult"]) -> None:
    s = False
    t = False
    for k, v in port_result.items():

        logger.error(
            "Throughput: "
            + f"Port Results  --  final: {not v.is_live} "
            + f"{k}: Frame Size: {v.current_packet_size} "
            + (f"Tx Off Rate(Percent): {v.rate} " if not v.is_common else "")
            + (f"Tx Act. Rate(Percent): {v.actual_rate} " if not v.is_common else "")
            + f"Tx(Frames): {float(v.tx_frames)} "
            + f"Tx Rate(L1)(Bits): {float(v.tx_rate_l1)} "
            + f"Tx Rate(L2)(Bits): {float(v.tx_rate_l2)} "
            + f"Tx Rate(Fps): {float(v.tx_fps)} "
            + f"Rx(Frames): {float(v.rx_frames)} "
            + f"Rx Rate(L1)(Bits): {float(v.rx_rate_l1)} "
            + f"Rx Rate(L2)(Bits): {float(v.rx_rate_l2)} "
            + f"Rx Rate(Fps): {float(v.rx_fps)} "
            + f"Loss(Frames): {float(v.loss_frames)} "
            + f"Loss Rate(Percent): {float(v.loss_ratio_pct)}% "
        )
        if not v.is_live:
            if v.test_result_state.value != "pending":
                t = True
            else:
                s = True
    if s:
        logger.error("=" * 100)
    if t:
        logger.error("#" * 100)


def show_all_latency_result(all_result: Dict[Tuple, "AllResult"]) -> None:
    logger.error("")
    logger.error("")
    for k, v in all_result.items():
        if not v.is_live:
            logger.error("=" * 100)
        logger.error(
            "Latency: "
            + f"All Results -- final: {not v.is_live} "
            + f"{k}: Frame Size: {v.current_packet_size} "
            + f"Result State: {v.test_result_state} "
            + f"Iter.#: {v.iteration} "
            + f"Tx Off Rate(Percent): {v.rate} "
            + (f"Tx Act. Rate(Percent): {v.actual_rate} " if not v.is_common else "")
            + f"Tx Rate(L1)(Bits): {float(v.tx_rate_l1)} "
            + f"Tx Rate(Fps): {float(v.tx_fps)} "
            + f"Tx(Frames): {float(v.tx_frames)} "
            + f"Rx(Frames): {float(v.rx_frames)} "
            + f"FCS Errors(Frames): {float(v.fcs_error)}] "
        )


def show_port_latency_result(port_result: Dict[Tuple, "PortResult"]) -> None:
    s = False
    for k, v in port_result.items():
        logger.error(
            "Latency: "
            f"Port Results  --  final: {not v.is_live} "
            + f"{k}: Frame Size: {v.current_packet_size} "
            + f"Result State: {v.test_result_state} "
            + f"Iter.#: {v.iteration} "
            + f"Tx(Frames): {float(v.tx_frames)} "
            + f"Rx(Frames): {float(v.rx_frames)} "
            + f"Latency(avg/min/max)(microsecs): {float(v.latency.average)}/{float(v.latency.minimum)}/{float(v.latency.maximum)} "
            + f"Jitter(avg/min/max)(microsecs): {float(v.jitter.average)}/{float(v.jitter.minimum)}/{float(v.jitter.maximum)} "
        )
        if not v.is_live:
            s = True
    if s:
        logger.error("=" * 100)


def show_all_frame_loss_result(all_result: Dict[Tuple, "AllResult"]) -> None:
    logger.error("")
    logger.error("")
    for k, v in all_result.items():
        if not v.is_live:
            logger.error("=" * 100)
        logger.error(
            "Frame Loss: "
            + f"All Results -- final: {not v.is_live} "
            + f"{k}: Frame Size: {v.current_packet_size} "
            + f"Result State: {v.test_result_state} "
            + f"Iter.#: {v.iteration if v.iteration > 0 else 'avg'} "
            + f"Tx Off Rate(Percent): {v.rate} "
            + (f"Tx Act. Rate(Percent): {v.actual_rate} " if not v.is_common else "")
            + f"Tx Rate(L1)(Bits): {float(v.tx_rate_l1)} "
            + f"Tx Rate(Fps): {float(v.tx_fps)} "
            + f"Tx(Frames): {float(v.tx_frames)} "
            + f"Rx(Frames): {float(v.rx_frames)} "
            + f"Rx Rate(L1)(Bits): {float(v.rx_rate_l1)} "
            + f"Rx Rate(Fps): {float(v.rx_fps)} "
            + f"Loss(Frames): {float(v.loss_frames)} "
            + f"Loss Rate(Percent): {float(v.loss_ratio_pct)}% "
            + f"FCS Errors(Frames): {float(v.fcs_error)}] "
        )


def show_port_frame_loss_result(port_result: Dict[Tuple, "PortResult"]) -> None:
    s = False
    for k, v in port_result.items():
        logger.error(
            "Frame Loss: "
            f"Port Results  --  final: {not v.is_live} "
            + f"{k}: Frame Size: {v.current_packet_size} "
            + f"Result State: {v.test_result_state} "
            + f"Iter.#: {v.iteration if v.iteration > 0 else 'avg'} "
            + f"Tx(Frames): {float(v.tx_frames)} "
            + f"Tx Rate(L1)(Bits): {float(v.tx_rate_l1)} "
            + f"Tx Rate(Fps): {float(v.tx_fps)} "
            + f"Rx(Frames): {float(v.rx_frames)} "
            + f"Rx Rate(L1)(Bits): {float(v.rx_rate_l1)} "
            + f"Rx Rate(Fps): {float(v.rx_fps)} "
        )
        if not v.is_live:
            s = True
    if s:
        logger.error("=" * 100)


def show_all_back_to_back_result(all_result: Dict[Tuple, "AllResult"]) -> None:
    logger.error("")
    logger.error("")
    for k, v in all_result.items():
        if not v.is_live:
            logger.error("=" * 100)
        logger.error(
            "Back-to-Back: "
            + f"All Results -- final: {not v.is_live} "
            + f"{k}: Frame Size: {v.current_packet_size} "
            + f"Result State: {v.test_result_state} "
            + f"Iter.#: {v.iteration} "
            + f"Tx Off Rate(Percent): {v.rate} "
            + (f"Tx Act. Rate(Percent): {v.actual_rate} " if not v.is_common else "")
            + f"Tx(Frames): {float(v.tx_frames)} "
            + f"Rx(Frames): {float(v.rx_frames)} "
            + f"Tx Burst(Frames): {float(v.burst_frames)} "
            + f"Tx Burst(Bytes) {float(v.burst_bytes)} "
            + f"Loss(Frames): {float(v.loss_frames)} "
            + f"Loss Rate(Percent): {float(v.loss_ratio_pct)}% "
            + f"FCS Errors(Frames): {float(v.fcs_error)}] "
        )


def show_port_back_to_back_result(port_result: Dict[Tuple, "PortResult"]) -> None:
    s = False
    for k, v in port_result.items():
        logger.error(
            "Back-to-Back: "
            f"Port Results  --  final: {not v.is_live} "
            + f"{k}: Frame Size: {v.current_packet_size} "
            + f"Result State: {v.test_result_state} "
            + f"Iter.#: {v.iteration} "
            + f"Tx Burst(Frames): {float(v.burst_frames)} "
            + f"Tx Burst(Bytes) {float(v.burst_bytes)} "
        )
        if not v.is_live:
            s = True
    if s:
        logger.error("=" * 100)
