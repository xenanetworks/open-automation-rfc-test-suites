from typing import List
from pydantic import BaseModel, Field, PositiveInt, NonNegativeInt
from xoa_driver import enums
from enum import Enum


class AutoNegotiationConf(BaseModel):
    enabled: bool = False
    an_good_check_retries: PositiveInt = 10


class CoeffAction(Enum):
    INC = "inc"
    DEC = "dec"


# class ELinkTrainCmdResults(Enum):
#     UNKNOWN = "unknown"
#     SUCCESS = "success"
#     TIMEOUT = "timeout"
#     FAILED = "failed"
#     COEFF_STS_NOT_UPDATED = "coeff_sts_not_updated"
#     COEFF_STS_UPDATED = "coeff_sts_updated"
#     COEFF_STS_AT_LIMIT = "coeff_sts_at_limit"
#     COEFF_STS_NOT_SUPPORTED = "coeff_sts_not_supported"
#     COEFF_STS_EQ_LIMIT = "coeff_sts_eq_limit"
#     COEFF_STS_C_AND_EQ_LIMIT = "coeff_sts_c_and_eq_limit"

#     def to_xmp(self) -> "enums.LinkTrainCmdResults":
#         return enums.LinkTrainCmdResults[self.name]


class BaseLinkTrainingConf(BaseModel):
    enabled: bool
    presets: List[int] = Field(..., ge=1, le=5)
    frame_lock_retries: PositiveInt = 20
    serdes: List[NonNegativeInt]
    # fail_criteria: List[ELinkTrainCmdResults]


class LtCoeffBoundaryMaxLimitLT(BaseLinkTrainingConf):
    coefficients: List[int] = Field(..., ge=-3, le=1)
    coeff_action: CoeffAction
    # stop_criteria: List[ELinkTrainCmdResults]


class LtCoeffBoundaryMinLimitLT(LtCoeffBoundaryMaxLimitLT):
    pass


class LtCoeffBoundaryEqLimitLT(LtCoeffBoundaryMaxLimitLT):
    pass


class LtPresetFrameLockLT(BaseLinkTrainingConf):
    waiting_time: int


class LtPresetConsistentFrameLockLT(LtPresetFrameLockLT):
    pass


class LtPresetPerformanceLT(LtPresetFrameLockLT):
    pass


class PrbsBer(BaseModel):
    polynomial: str
    duration: int


class LtBase(BaseModel):
    enabled: bool
    repetitions: int
    auto_negotiation: AutoNegotiationConf


class LtCoeffBoundaryMaxLimit(LtBase):
    link_training: LtCoeffBoundaryMaxLimitLT


class LtCoeffBoundaryMinLimit(LtBase):
    link_training: LtCoeffBoundaryMinLimitLT


class LtCoeffBoundaryEqLimit(LtBase):
    link_training: LtCoeffBoundaryEqLimitLT


class LtPresetFrameLock(LtBase):
    link_training: LtPresetFrameLockLT


class LtPresetPerformance(LtBase):
    link_training: LtPresetPerformanceLT


class TestTypesConfig(BaseModel):
    lt_coeff_boundary_max_limit: LtCoeffBoundaryMaxLimit
    lt_coeff_boundary_min_limit: LtCoeffBoundaryMinLimit
    lt_coeff_boundary_eq_limit: LtCoeffBoundaryEqLimit
    lt_preset_frame_lock: LtPresetFrameLock
    lt_preset_performance: LtPresetPerformance
