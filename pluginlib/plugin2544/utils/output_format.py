LATENCY_OUTPUT = {
    "test_suite_type": ...,
    "result_state": ...,
    "test_case_type": ...,
    "tx_rate_percent": ...,
    "tx_rate_nominal_percent": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "total": {
        "tx_counter": {"frames", "l1_bps", "fps"},
        "rx_counter": {"frames"},
        "fcs_error_frames": ...,
    },
    "port_data": {
        "__all__": {
            "port_id": ...,
            "tx_counter": {"frames"},
            "rx_counter": {"frames"},
            "latency": {"average", "minimum", "maximum"},
            "jitter": {"average", "minimum", "maximum"},
        }
    },
}

FRAME_LOSS_OUTPUT = {
    "test_suite_type": ...,
    "test_case_type": ...,
    "result_state": ...,
    "tx_rate_percent": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "total": {
        "tx_counter": {"frames", "l1_bps", "fps"},
        "rx_counter": {"frames", "l1_bps", "fps"},
        "rx_loss_frames": ...,
        "rx_loss_percent": ...,
        "fcs_error_frames": ...,
    },
    "port_data": {
        "__all__": {
            "port_id": ...,
            "tx_counter": {"frames", "l1_bps", "fps"},
            "rx_counter": {"frames", "l1_bps", "fps"},
        }
    },
}


THROUGHPUT_PER_PORT = {
    "test_suite_type": ...,
    "test_case_type": ...,
    "result_state": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "rate_result_scope": ...,
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
    "port_data": {
        "__all__": {
            "rate": ...,
            "port_id": ...,
            "actual_rate": ...,
            "tx_counter": {"frames", "l1_bps", "l2_bps", "fps"},
            "rx_counter": {"frames", "l1_bps", "l2_bps", "fps"},
            "loss_frames": ...,
            "loss_ratio": ...,
        }
    },
}

THROUGHPUT_COMMON = {
    "test_suite_type": ...,
    "test_case_type": ...,
    "result_state": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "tx_rate_percent": ...,
    "rate_result_scope": ...,
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
    "port_data": {
        "__all__": {
            "port_id": ...,
            "tx_counter": {"frames", "l1_bps", "l2_bps", "fps"},
            "rx_counter": {"frames", "l1_bps", "l2_bps", "fps"},
            "loss_frames": ...,
            "loss_ratio": ...,
        }
    },
}


BACKTOBACKOUTPUT = {
    "test_suite_type": ...,
    "test_case_type": ...,
    "result_state": ...,
    "tx_rate_percent": ...,
    "is_final": ...,
    "frame_size": ...,
    "repetition": ...,
    "total": {
        "tx_counter": {"frames"},
        "rx_counter": {"frames"},
        "tx_burst_frames": ...,
        "tx_burst_bytes": ...,
        "rx_loss_frames": ...,
        "rx_loss_percent": ...,
        "fcs_error_frames": ...,
    },
    "port_data": {
        "__all__": {
            "port_id": ...,
            "burst_frames": ...,
            "burst_bytes_count": ...,
        }
    },
}