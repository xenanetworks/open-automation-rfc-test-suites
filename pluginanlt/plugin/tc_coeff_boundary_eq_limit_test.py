from __future__ import annotations
from typing import Generator
from xoa_driver.enums import LinkTrainCmdResults, LinkTrainCoeffs
from xoa_driver.hlfuncs import anlt
from .tc_base import TcBase
from .statistics import StLtCoeffBoundaryEqLimit
from dataclasses import asdict


class TcCoeffBoundaryEqLimitTest(TcBase):
    def enabled(self) -> bool:
        return self.resources.test_types_conf.lt_coeff_boundary_eq_limit.enabled

    def prepare_phase(self) -> None:
        super().prepare_phase()
        self.check_lt_coding = False
        self.repeat_times = 1000
        self.sleep_time = 0.1
        self.statistic = StLtCoeffBoundaryEqLimit()

    def data_phase(self) -> tuple[bool, int, int]:
        base = self.resources.test_types_conf.lt_coeff_boundary_eq_limit
        should_an = base.auto_negotiation.enabled
        an_good_check_retries = base.auto_negotiation.an_good_check_retries
        frame_lock_retries = base.link_training.frame_lock_retries
        return should_an, an_good_check_retries, frame_lock_retries

    def loop_phase(self) -> Generator[tuple[int, ...], None, None]:
        base = self.resources.test_types_conf.lt_coeff_boundary_eq_limit
        repetitions = base.repetitions
        serdess = base.link_training.serdes
        presets = base.link_training.presets
        coeffs = base.link_training.coefficients
        return self._loop_gen(repetitions, serdess, presets, coeffs)

    async def run_func(self, repetition: int, serdes: int, preset: int, coeff: int) -> bool:
        port = self.resources.port
        self.statistic.repetition = repetition
        self.statistic.serdes_index = serdes
        self.statistic.preset = preset
        self.statistic.coefficient = coeff
        real_coeff = self.convert_coeff(coeff)
        resp = await anlt.lt_coeff_inc(port, serdes, LinkTrainCoeffs(real_coeff))
        if resp in (
            LinkTrainCmdResults.COEFF_STS_EQ_LIMIT,
            LinkTrainCmdResults.COEFF_STS_C_AND_EQ_LIMIT,
            LinkTrainCmdResults.COEFF_STS_AT_LIMIT,
            LinkTrainCmdResults.COEFF_STS_NOT_SUPPORTED
        ):
            self.statistic.status = "success"
            self.resources.xoa_out.send_statistics(asdict(self.statistic))
            return True
        elif resp == LinkTrainCmdResults.TIMEOUT:
            self.statistic.status = "fail"
            self.resources.xoa_out.send_statistics(asdict(self.statistic))
            return True
        return False
