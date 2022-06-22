LATENCY_OUTPUT = {
    "test_suit_type": ...,
    "result_state": ...,
    "test_case_type": ...,
    "tx_rate_percent": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "port_data": {
        "__all__": {
            "port_id": ...,
            "tx_counter": {"frames"},
            "rx_counter": {"frames"},
            "latency": {"average", "minimum", "maximum"},
            "jitter": {"average", "minimum", "maximum"},
        }
    },
    "total": {
        "tx_counter": {"frames", "l1_bps", "fps"},
        "rx_counter": {"frames"},
        "fcs_error_frames": ...,
    },
}

FRAME_LOSS_OUTPUT = {
    "test_suit_type": ...,
    "test_case_type": ...,
    "result_state": ...,
    "tx_rate_percent": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "port_data": {
        "__all__": {
            "tx_counter": {"frames", "l1_bps", "fps"},
            "rx_counter": {"frames", "l1_bps", "fps"},
        }
    },
    "total": {
        "tx_counter": {"frames", "l1_bps", "fps"},
        "rx_counter": {"frames", "l1_bps", "fps"},
        "rx_loss_frames": ...,
        "rx_loss_percent": ...,
        "fcs_error_frames": ...,
    },
}


THROUGHPUT_PER_PORT = {
    "test_suit_type": ...,
    "test_case_type": ...,
    "result_state": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "port_data": {
        "__all__": {
            "rate": ...,
            "actual_rate": ...,
            "tx_counter": {"frames", "l1_bps", "l2_bps", "fps"},
            "rx_counter": {"frames", "l1_bps", "l2_bps", "fps"},
            "loss_frames": ...,
            "loss_ratio": ...,
        }
    },
    "total": {
        "tx_counter": {"frames", "l1_bps", "l2_bps", "fps"},
        "rx_counter": {"frames"},
        "rx_loss_frames": ...,
        "rx_loss_percent": ...,
        "fcs_error_frames": ...,
        "tx_rate_l1_bps_theor": ...,
        "tx_rate_fps_theor": ...,
        "ber": ...,
    },
}

THROUGHPUT_COMMON = {
    "test_suit_type": ...,
    "test_case_type": ...,
    "result_state": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "port_data": {
        "__all__": {
            "tx_counter": {"frames", "l1_bps", "l2_bps", "fps"},
            "rx_counter": {"frames", "l1_bps", "l2_bps", "fps"},
            "loss_frames": ...,
            "loss_ratio": ...,
        }
    },
    "total": {
        "tx_counter": {"frames", "l1_bps", "fps"},
        "rx_counter": {"frames", "l1_bps", "fps"},
        "rx_loss_frames": ...,
        "rx_loss_percent": ...,
        "fcs_error_frames": ...,
        "tx_rate_l1_bps_theor": ...,
        "tx_rate_fps_theor": ...,
        "ber": ...,
    },
}


BACKTOBACKOUTPUT = {
    "test_suit_type": ...,
    "test_case_type": ...,
    "result_state": ...,
    "tx_rate_percent": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "port_data": {
        "__all__": {
            "burst_frames": ...,
            "burst_bytes_count": ...,
        }
    },
    "total": {
        "tx_counter": {"frames"},
        "rx_counter": {"frames"},
        "tx_burst_frames": ...,
        "tx_burst_bytes": ...,
        "rx_loss_frames": ...,
        "rx_loss_percent": ...,
        "fcs_error_frames": ...,
    },
}