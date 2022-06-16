from copy import deepcopy
from decimal import Decimal
from typing import List, Optional, Union

from loguru import logger
from .statistics import FinalStatistic
from .test_resource import ResourceManager

from .structure import PortStruct
from ..model import ThroughputTest


class ThroughputBoutEntry:
    def __init__(self, throughput_conf: ThroughputTest, port_structs: List[PortStruct]):
        self.current = (
            self.rate
        ) = self.next = throughput_conf.rate_iteration_options.initial_value_pct
        self.left_bound: Decimal = (
            throughput_conf.rate_iteration_options.minimum_value_pct
        )
        self.right_bound: Decimal = (
            throughput_conf.rate_iteration_options.maximum_value_pct
        )
        self._last_move: int = 0
        self.port_structs = port_structs
        self.throughput_conf = throughput_conf
        self.best_final_result: FinalStatistic
        self.port_test_passed = False
        self.port_should_continue = True

    def update_left_bound(self):
        self.left_bound = self.current
        self._last_move = -1
        if (
            abs((self.left_bound + self.right_bound) / 2 - self.left_bound)
            < self.throughput_conf.rate_iteration_options.value_resolution_pct
        ):
            self.next = self.right_bound
            self.left_bound = self.right_bound
        else:
            self.next = (self.left_bound + self.right_bound) / 2

    def update_right_bound(self, loss_ratio: Decimal):
        self.right_bound = self.current
        self._last_move = 1

        if (
            abs((self.left_bound + self.right_bound) / 2 - self.right_bound)
            < self.throughput_conf.rate_iteration_options.value_resolution_pct
        ):
            self.next = self.left_bound
            self.right_bound = self.left_bound
        if self.throughput_conf.rate_iteration_options.search_type.is_fast:
            self.next = max(
                self.current * (Decimal("1.0") - loss_ratio),
                self.left_bound,
            )
        else:
            self.next = (self.left_bound + self.right_bound) / 2

    def compare_search_pointer(self) -> bool:
        return self.next == self.current

    def pass_threshold(self) -> bool:
        return (
            self.current >= self.throughput_conf.pass_threshold_pct
            if self.throughput_conf.use_pass_threshold
            else True
        )

    def update_rate(self):
        self.current = self.next
        self.rate = self.next
        for port_struct in self.port_structs:
            port_struct.rate = self.rate
            logger.info(f'{port_struct.port_identity.name}  rate to {self.rate}')

    def update_boundary(self, result: Optional[FinalStatistic]):
        self.port_should_continue = False
        self.port_test_passed = False
        if not result:
            self.port_should_continue = True
        else:
            if (
                self.throughput_conf.rate_iteration_options.result_scope.is_per_source_port
            ):
                loss_ratio = self.port_structs[0].statistic.loss_ratio
            else:
                loss_ratio = result.total.rx_loss_percent
            loss_ratio_pct = loss_ratio * 100
            if loss_ratio_pct <= self.throughput_conf.acceptable_loss_pct:
                if (
                    self.throughput_conf.rate_iteration_options.result_scope.is_per_source_port
                ):
                    [
                        stream_struct.set_best_result()
                        for stream_struct in self.port_structs[0].stream_structs
                    ]
                else:
                    self.best_final_result = result
                self.update_left_bound()
            else:
                self.update_right_bound(loss_ratio)
            if self.compare_search_pointer():
                self.port_test_passed = self.pass_threshold()
            else:
                self.port_should_continue = True


def get_initial_boundaries(throughput_conf: ThroughputTest, resources: ResourceManager):
    if throughput_conf.rate_iteration_options.result_scope.is_per_source_port:
        return [
            ThroughputBoutEntry(throughput_conf, [port_struct])
            for port_struct in resources.port_structs
        ]
    else:
        return [ThroughputBoutEntry(throughput_conf, resources.port_structs)]
