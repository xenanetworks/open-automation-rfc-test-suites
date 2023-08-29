from __future__ import annotations
import asyncio
from typing import Any, Generator
from xoa_driver import enums
from xoa_driver.hlfuncs import anlt, mgmt
from .tc_base import TcBase
from .statistics import StLtPresetPerformance
from dataclasses import asdict


class TcPresetPerformance(TcBase):
    def enabled(self) -> bool:
        return self.resources.test_types_conf.lt_preset_performance.enabled

    def prepare_phase(self) -> None:
        super().prepare_phase()
        self.statistic = StLtPresetPerformance()

    def data_phase(self) -> tuple[bool, int, int]:
        base = self.resources.test_types_conf.lt_preset_performance
        should_an = base.auto_negotiation.enabled
        an_good_check_retries = base.auto_negotiation.an_good_check_retries
        frame_lock_retries = base.link_training.frame_lock_retries
        return should_an, an_good_check_retries, frame_lock_retries

    def loop_phase(self) -> Generator[tuple[int, ...], None, None]:
        base = self.resources.test_types_conf.lt_preset_performance
        repetitions = base.repetitions
        serdess = base.link_training.serdes
        presets = base.link_training.presets
        coeffs = [-9999]
        return self._loop_gen(repetitions, serdess, presets, coeffs)

    async def run_func(self, repetition: int, serdes: int, preset: int, coeffs: int) -> bool:
        port = self.resources.port
        self.statistic.repetition = repetition
        self.statistic.serdes_index = serdes
        self.statistic.preset = preset
        self.statistic.status = 'success'
        self.resources.xoa_out.send_statistics(asdict(self.statistic))
        # measure PRBS BER in Data phase
        resp = await anlt.lt_status(port=port, serdes=serdes)
        _lt_ber = resp['ber']
        # logger.warning(f"Total bits        : {resp_dict['total_bits']:,}")
        # logger.warning(f"Total err. bits   : {resp_dict['total_errored_bits']:,}")
        # logger.warning(f"BER               : {resp_dict['ber']}")

        # stop anlt on the port because we will move to DATA Phase
        await anlt.anlt_stop(port)

        await asyncio.sleep(1)
        await port.pcs_pma.prbs_config.type.set(
            prbs_inserted_type=enums.PRBSInsertedType.PHY_LINE,
            polynomial=enums.PRBSPolynomial.PRBS31,
            invert=enums.PRBSInvertState.NON_INVERTED,
            statistics_mode=enums.PRBSStatisticsMode.PERSECOND,
        )
        # Enable PRBS-31 measurement
        await port.ser_des[serdes].prbs.tx_config.set(
            prbs_seed=0,
            prbs_on_off=enums.PRBSOnOff.PRBSON,
            error_on_off=enums.ErrorOnOff.ERRORSON,
        )
        resp = await port.ser_des[serdes].prbs.status.get()

        _lock_status = resp.lock.name
        _prbr_bits = resp.byte_count * 8
        _error_bits = resp.error_count
        _prbs_ber = _error_bits / _prbr_bits

        # logger.info(f"Serdes {serdes}")
        # logger.info(f"PRBS Lock: {_lock_status}")
        # logger.info(f"PRBS Bits: {_prbr_bits}")
        # logger.info(f"PRBS Errors: {_error_bits}")
        # logger.info(f"PRBS-31 BER: {_prbs_ber}")

        # Disable PRBS-31 measurement
        await port.ser_des[serdes].prbs.tx_config.set(
            prbs_seed=0,
            prbs_on_off=enums.PRBSOnOff.PRBSOFF,
            error_on_off=enums.ErrorOnOff.ERRORSOFF,
        )
        self.statistic.lt_ber = _lt_ber
        self.statistic.prbs_ber = _prbs_ber
        self.resources.xoa_out.send_statistics(asdict(self.statistic))
        # free the port
        await mgmt.free_port(port)
