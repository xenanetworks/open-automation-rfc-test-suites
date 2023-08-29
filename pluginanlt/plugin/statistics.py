from __future__ import annotations
from dataclasses import dataclass


@dataclass
class BaseStatistics:
    module_index: int = -1
    port_index: int = -1
    serdes_index: int = -1
    an_status: str = 'unknown'
    status: str = 'pending'
    lt_local_frame_lock: bool = False
    lt_remote_frame_lock: bool = False
    repetition: int = 0
    timestamp: float = 0.0
    preset: int = -1


@dataclass
class StLtCoeffBoundaryMaxLimit(BaseStatistics):
    coefficient: int = -9999
    response: str = 'pending'


@dataclass
class StLtCoeffBoundaryEqLimit(StLtCoeffBoundaryMaxLimit):
    pass


@dataclass
class StLtCoeffBoundaryMinLimit(StLtCoeffBoundaryMaxLimit):
    pass


@dataclass
class StLtPresetFrameLock(BaseStatistics):
    pass


@dataclass
class StLtPresetPerformance(BaseStatistics):
    lt_ber: float = 0.0
    prbs_ber: float = 0.0
