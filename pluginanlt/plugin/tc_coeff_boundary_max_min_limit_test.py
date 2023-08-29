from __future__ import annotations
from typing import Any, Generator, Union, Literal
from xoa_driver.enums import LinkTrainCoeffs, LinkTrainCmdResults
from xoa_driver.hlfuncs import anlt
from .tc_base import TcBase
from . statistics import StLtCoeffBoundaryMaxLimit, StLtCoeffBoundaryMinLimit


class TcCoeffBoundaryMaxMinLimitTest(TcBase):

    def prepare_phase(self) -> None:
        super().prepare_phase()
        self.repeat_times = 1000
        self.sleep_time = 0
        self.statistic = StLtCoeffBoundaryMaxLimit()

    def data_base(self, typess: Union[Literal['max'], Literal['min']]) -> tuple[Any, ...]:
        base = self.resources.test_types_conf.lt_coeff_boundary_max_limit if typess == 'max' else self.resources.test_types_conf.lt_coeff_boundary_min_limit
        should_an = base.auto_negotiation.enabled
        an_good_check_retries = base.auto_negotiation.an_good_check_retries
        frame_lock_retries = base.link_training.frame_lock_retries
        return should_an, an_good_check_retries, frame_lock_retries

    def loop_base(self, typess: Union[Literal['max'], Literal['min']]) -> Generator[tuple[int, ...], None, None]:
        base = self.resources.test_types_conf.lt_coeff_boundary_max_limit if typess == 'max' else self.resources.test_types_conf.lt_coeff_boundary_min_limit
        repetitions = base.repetitions
        serdess = base.link_training.serdes
        presets = base.link_training.presets
        coeffs = base.link_training.coefficients
        return self._loop_gen(repetitions, serdess, presets, coeffs)

    async def run_func_base(self, typess: str, repetition: int, serdes: int, preset: int, coeff: int) -> bool:
        port = self.resources.port
        self.statistic.repetition = repetition
        self.statistic.serdes_index = serdes
        self.statistic.preset = preset
        self.statistic.coefficient = coeff
        if typess == 'max':
            func = anlt.lt_coeff_inc
            cnuf = anlt.lt_coeff_dec
        else:
            func = anlt.lt_coeff_dec
            cnuf = anlt.lt_coeff_inc
        real_coeff = self.convert_coeff(coeff)
        lt_coeff = LinkTrainCoeffs(real_coeff)
        rt_coeff = {
            LinkTrainCoeffs.PRE3: LinkTrainCoeffs.MAIN,
            LinkTrainCoeffs.PRE2: LinkTrainCoeffs.MAIN,
            LinkTrainCoeffs.PRE: LinkTrainCoeffs.MAIN,
            LinkTrainCoeffs.MAIN: LinkTrainCoeffs.PRE,
            LinkTrainCoeffs.POST: LinkTrainCoeffs.MAIN
        }[lt_coeff]

        resp = await func(port, serdes, LinkTrainCoeffs(coeff - 1))
        if resp in (
            LinkTrainCmdResults.COEFF_STS_AT_LIMIT,
            LinkTrainCmdResults.COEFF_STS_NOT_SUPPORTED,
        ):
            self.statistic.status = 'success'
            return True
        elif resp == LinkTrainCmdResults.TIMEOUT:
            self.statistic.status = 'fail'
            return True
        elif resp == (LinkTrainCmdResults.COEFF_STS_EQ_LIMIT):
            resp = await cnuf(port, serdes, rt_coeff)
            if resp == LinkTrainCmdResults.TIMEOUT:
                self.statistic.status = 'fail'
                return True
        return False


class TcCoeffBoundaryMaxLimitTest(TcCoeffBoundaryMaxMinLimitTest):
    def prepare_phase(self) -> None:
        super().prepare_phase()
        self.statistic = StLtCoeffBoundaryMaxLimit()

    def enabled(self) -> bool:
        return self.resources.test_types_conf.lt_coeff_boundary_max_limit.enabled

    def data_phase(self) -> tuple[bool, int, int]:
        return self.data_base('max')

    def loop_phase(self) -> Generator[tuple[int, int], None, None]:
        return self.loop_base('max')

    async def run_func(self, repetition: int, serdes: int, preset: int, coeff: int) -> bool:
        return await self.run_func_base('max', repetition, serdes, preset, coeff)


class TcCoeffBoundaryMinLimitTest(TcCoeffBoundaryMaxMinLimitTest):
    def prepare_phase(self) -> None:
        super().prepare_phase()
        self.statistic = StLtCoeffBoundaryMinLimit()

    def enabled(self) -> bool:
        return self.resources.test_types_conf.lt_coeff_boundary_min_limit.enabled

    def data_phase(self) -> tuple[bool, int, int]:
        return self.data_base('min')

    def loop_phase(self) -> Generator[tuple[int, int], None, None]:
        return self.loop_base('min')

    async def run_func(self, repetition: int, coeff: int, preset: int, serdes: int) -> bool:
        return await self.run_func_base('min', repetition, serdes, preset, coeff)
