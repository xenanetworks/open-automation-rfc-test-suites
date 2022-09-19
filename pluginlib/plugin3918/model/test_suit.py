from pydantic import BaseModel, NonNegativeInt 
from ..utils.constants import RDisplayUnit, RFlowCreationType, RLatencyMode, RTidAllocationScope
from .test_config import FrameSizeConfiguration


class TestConfiguration3918(BaseModel):
    tid_offset: NonNegativeInt
    flow_creation_type: RFlowCreationType
    mac_base_address: str
    use_gateway_mac_as_dmac: bool
    enable_multi_stream: bool
    per_port_stream_count: int
    multi_stream_address_offset: int
    multi_stream_address_increment: int
    multi_stream_mac_base_address: str
    use_micro_tpld_on_demand: bool
    latency_mode: RLatencyMode
    latency_display_unit: RDisplayUnit
    jitter_display_unit: RDisplayUnit
    toggle_sync_state: bool
    sync_off_duration: int
    tid_allocation_scope: RTidAllocationScope
    frame_sizes: FrameSizeConfiguration


