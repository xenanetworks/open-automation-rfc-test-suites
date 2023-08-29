from __future__ import annotations
import asyncio
from xoa_driver import enums
from xoa_driver.hlfuncs import mgmt, anlt
from xoa_driver.internals import commands
from typing import Any, Callable, Generator
from .test_resource import ResourceManagerAnlt, FreyaModuleIns, FreyaPortIns
from ..utils.exceptions import NotFreyaModuleError, NotFreyaPortError
from .statistics import BaseStatistics
from dataclasses import asdict


class TcBase:
    def __init__(self, resources: "ResourceManagerAnlt") -> None:
        self.resources = resources
        self.repeat_times = 1
        self.sleep_time = 0
        self.statistic = BaseStatistics()

    def convert_coeff(self, coeff: int) -> int:
        dic = {
            -1: enums.LinkTrainCoeffs.PRE,
            0: enums.LinkTrainCoeffs.MAIN,
            1: enums.LinkTrainCoeffs.POST,
            -2: enums.LinkTrainCoeffs.PRE2,
            -3: enums.LinkTrainCoeffs.PRE3,
        }
        return dic[coeff]

    async def _check_an_status_func(self) -> bool:
        port = self.resources.port
        resp = await port.pcs_pma.auto_neg.status.get()
        self.statistic.an_status = resp.auto_state.name.lower()
        return resp.auto_state.value == enums.AutoNegStatus.AN_GOOD_CHECK.value

    async def check_an_status(self, retry: int = 10) -> bool:
        return await self._retry_func(self._check_an_status_func, tuple(), retry, 0.1)

    async def start_anlt_phase(self) -> bool:
        # tester = self.resources.tester
        module = self.resources.module

        # the module must be a freya module
        if not isinstance(module, FreyaModuleIns):
            raise NotFreyaModuleError(module.module_id, type(module))

        # resp1 = await module.media.get()

        # access port on the module and # logger.info out the actual media config
        port = self.resources.port
        if not isinstance(port, FreyaPortIns):
            raise NotFreyaPortError(port.kind.module_id, port.kind.port_id, type(port))

        # p_count = len(module.ports)
        # resp2 = await port.speed.current.get()
        # p_speed = resp.port_speed

        # get serdes count on the port
        resp = await port.capabilities.get()
        serdes_cnt = resp.serdes_count

        # show port media type etc

        # reserve the port and reset the port
        await mgmt.free_module(module, should_free_ports=True)
        await mgmt.reserve_port(port)
        await mgmt.reset_port(port)
        # autotune taps
        for serdes_idx in range(serdes_cnt):
            await port.ser_des[serdes_idx].phy.autotune.set(on_off=enums.OnOff.OFF)
            await port.ser_des[serdes_idx].phy.autotune.set(on_off=enums.OnOff.ON)

        # config link recovery (anlt recovery --off)
        await anlt.anlt_link_recovery(port=port, enable=False)

        await anlt.anlt_start(
            port=port,
            should_do_an=False,
            should_do_lt=True,
            should_lt_interactive=True,
            an_allow_loopback=False,
            lt_preset0=enums.NRZPreset.NRZ_NO_PRESET,
            lt_initial_modulations={},
            lt_algorithm={},
        )
        return True

    async def anlt_stop(self) -> None:
        port = self.resources.port
        await mgmt.reserve_port(port)
        await anlt.anlt_stop(port)

    async def verify_both_see_frame_lock(
        self, serdes: int, retry: int = 20, change_stat: bool = False
    ) -> bool:
        return await self._retry_func(
            self._verify_both, (serdes, change_stat), retry, 0.1
        )

    async def _verify_both(self, serdes: int, change_stat: bool) -> bool:
        port = self.resources.port
        conn, mid, pid = anlt.get_ctx(port)
        lt_info = await commands.PL1_LINKTRAININFO(conn, mid, pid, serdes, 0).get()
        local = lt_info.frame_lock.value
        self.statistic.lt_local_frame_lock = bool(local)
        remote = lt_info.remote_frame_lock.value
        self.statistic.lt_remote_frame_lock = bool(remote)
        return (
            local == enums.LinkTrainFrameLock.LOCKED.value
            and remote == enums.LinkTrainFrameLock.LOCKED.value
        )

    def _loop_gen(
        self, a: int, b: list[int], c: list[int], d: list[int]
    ) -> Generator[tuple[int, ...], None, None]:
        for i in range(1, a + 1):
            for j in b:
                for k in c:
                    for li in d:
                        yield i, j, k, li

    async def an_status_phase(
        self, should_an: bool, an_good_check_retries: int
    ) -> bool:
        if should_an and (not await self.check_an_status(retry=an_good_check_retries)):
            self.statistic.status = 'fail'
            self.resources.xoa_out.send_statistics(asdict(self.statistic))
            await self.anlt_stop()
            return False
        return True

    async def frame_status_phase(self, serdes: int, frame_lock_retries: int) -> bool:
        frame_lock_detected = await self.verify_both_see_frame_lock(serdes, frame_lock_retries)
        if not frame_lock_detected:
            self.statistic.status = 'fail'
            self.resources.xoa_out.send_statistics(asdict(self.statistic))
            await self.anlt_stop()
            return False
        return True

    async def switch_pam4_phase(self, serdes: int) -> bool:
        resp = await anlt.lt_encoding(port=self.resources.port, serdes=serdes, encoding=enums.LinkTrainEncoding.PAM4)
        if resp != enums.LinkTrainCmdResults.SUCCESS:
            self.statistic.status = 'fail'
            self.resources.xoa_out.send_statistics(asdict(self.statistic))
            await self.anlt_stop()
            return False
        return True

    async def preset_phase(self, serdes: int, preset: int) -> bool:
        resp = await anlt.lt_preset(
            port=self.resources.port, serdes=serdes, preset=enums.LinkTrainPresets(preset)
        )
        if resp != enums.LinkTrainCmdResults.SUCCESS:
            await self.anlt_stop()
            return False
        return True

    async def common(self, should_an: bool, an_good_check_retries: int, serdes: int, frame_lock_retries: int) -> bool:
        for m in (self.start_anlt_phase(), self.an_status_phase(should_an, an_good_check_retries),
                  self.frame_status_phase(serdes, frame_lock_retries), self.switch_pam4_phase(serdes),
                  self.frame_status_phase(serdes, frame_lock_retries), self.frame_status_phase(serdes, frame_lock_retries)):
            if not await m:
                return False
        return True

    async def run(self) -> None:
        if not self.enabled():
            return None
        port = self.resources.port
        should_an, an_good_check_retries, frame_lock_retries = self.data_phase()
        self.prepare_phase()
        for repetition, serdes, preset, coeff in self.loop_phase():
            if not self.common(should_an, an_good_check_retries, serdes, frame_lock_retries):
                continue
            # Request the remote port to use the specified preset
            await self._retry_func(
                self.run_func,
                (repetition, serdes, preset, coeff),
                self.repeat_times,
                self.sleep_time,
            )
        await anlt.anlt_stop(port)
        await mgmt.free_port(port)

    async def _retry_func(
        self,
        coro: Callable,
        args_tuple: tuple[Any, ...],
        times: int = 1,
        sleep: float = 0,
    ) -> bool:
        quitt = False
        for _ in range(times):
            quitt = await coro(*args_tuple)
            if quitt:
                break
            await asyncio.sleep(sleep)
        return quitt

    def enabled(self) -> bool:
        return False

    def prepare_phase(self) -> None:
        pass

    def data_phase(self) -> tuple[bool, int, int]:
        return (False, 0, 0)

    def loop_phase(self) -> list[tuple[int, ...]]:
        return []

    async def run_func(self, repetition: int, serdes: int, preset: int, coeff: int) -> bool:
        return False
