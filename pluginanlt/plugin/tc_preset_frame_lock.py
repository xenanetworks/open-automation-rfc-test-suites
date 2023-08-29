from __future__ import annotations
from typing import Generator
from .tc_base import TcBase
from .statistics import StLtPresetFrameLock
from dataclasses import asdict


class TcPresetFrameLock(TcBase):
    def prepare_phase(self) -> None:
        super().prepare_phase()
        self.statistics = StLtPresetFrameLock()

    def enabled(self) -> bool:
        return self.resources.test_types_conf.lt_preset_frame_lock.enabled

    def data_phase(self) -> tuple[bool, int, int]:
        base = self.resources.test_types_conf.lt_preset_frame_lock
        should_an = base.auto_negotiation.enabled
        an_good_check_retries = base.auto_negotiation.an_good_check_retries
        frame_lock_retries = base.link_training.frame_lock_retries
        return should_an, an_good_check_retries, frame_lock_retries

    def loop_phase(self) -> Generator[tuple[int, ...], None, None]:
        base = self.resources.test_types_conf.lt_preset_frame_lock
        repetitions = base.repetitions
        serdess = base.link_training.serdes
        presets = base.link_training.presets
        coeffs = [-9999]
        return self._loop_gen(repetitions, serdess, presets, coeffs)

    async def run_func(self, repetition: int, serdes: int, preset: int, coeffs: int) -> bool:
        self.statistic.repetition = repetition
        self.statistic.serdes_index = serdes
        self.statistic.preset = preset
        self.statistic.status = 'success'
        self.resources.xoa_out.send_statistics(asdict(self.statistic))
        return True
