from decimal import Decimal
from ..model.m_test_type_config import BackToBackTest
from .structure import PortStruct


class BackToBackBoutEntry:
    def __init__(
        self,
        test_type_conf: BackToBackTest,
        port_struct: PortStruct,
        frame_size: Decimal,
        rate: Decimal,
    ):
        self._test_type_conf = test_type_conf
        self._port_struct = port_struct
        self._frame_size = frame_size
        self._left_bound: Decimal = Decimal("0")
        self._right_bound = self.current = self.next = (
            self._test_type_conf.common_options.actual_duration * rate / Decimal("100")
        )
        self._last_move: int = 0
        self._port_should_continue: bool = False
        self._port_test_passed: bool = False
        self._port_struct.clear_counter()

    @property
    def port_should_continue(self) -> bool:
        return self._port_should_continue

    @property
    def port_test_passed(self) -> bool:
        return self._port_test_passed

    def update_boundaries(self) -> None:
        self._port_should_continue = self._port_test_passed = False
        if not self._port_struct.statistic or (self._port_struct.statistic and not self._port_struct.statistic.is_final):
            self._port_should_continue = True
            return
        if self._left_bound <= self._right_bound:

            if (
                self._port_struct.statistic
                and self._port_struct.statistic.loss_ratio == Decimal("0")
            ):
                self.update_left_bound()
            else:
                self.update_right_bound()
            if self.compare_search_pointer():
                self._port_test_passed = True
            else:
                self._port_should_continue = True
        self.current = self.next

    def update_left_bound(self) -> None:
        self._left_bound = self.current
        self.next = (self._left_bound + self._right_bound) / 2
        self._last_move = -1

    def update_right_bound(self) -> None:
        self._right_bound = self.current
        self.next = (self._left_bound + self._right_bound) / 2

        self._last_move = 1

    def compare_search_pointer(self) -> bool:
        res = self._test_type_conf.rate_sweep_options.burst_resolution
        if abs(self.next - self.current) <= res:
            if self.next >= self.current:
                # make sure we report the right boundary if we are so close to it.
                if (self._right_bound - self.current) <= res:
                    self.current = self._right_bound
            else:
                if (self.current - self._left_bound) <= res:
                    self.current = self._left_bound
            return True
        return False
