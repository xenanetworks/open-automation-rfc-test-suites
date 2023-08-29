from __future__ import annotations
from typing import TYPE_CHECKING, Union, Dict
from pydantic import BaseModel
from xoa_driver import ports, modules, testers
if TYPE_CHECKING:
    from xoa_core.core.test_suites.datasets import PortIdentity
    from ..dataset import ModelAnlt, TestTypesConfig
    from ..utils.interfaces import TestSuitePipe

FreyaPort = Union[ports.PFreya800G1S1P_a, ports.PFreya800G1S1P_b, ports.PFreya800G1S1POSFP_a, ports.PFreya800G4S1P_a, ports.PFreya800G4S1P_b, ports.PFreya800G4S1POSFP_a]
FreyaPortIns = (ports.PFreya800G1S1P_a, ports.PFreya800G1S1P_b, ports.PFreya800G1S1POSFP_a, ports.PFreya800G4S1P_a, ports.PFreya800G4S1P_b, ports.PFreya800G4S1POSFP_a)
FreyaModule = Union[modules.MFreya800G1S1P_a, modules.MFreya800G1S1P_b, modules.MFreya800G1S1POSFP_a,
                    modules.MFreya800G4S1P_a, modules.MFreya800G4S1P_b, modules.MFreya800G4S1POSFP_a]
FreyaModuleIns = (modules.MFreya800G1S1P_a, modules.MFreya800G1S1P_b, modules.MFreya800G1S1POSFP_a,
                  modules.MFreya800G4S1P_a, modules.MFreya800G4S1P_b, modules.MFreya800G4S1POSFP_a)


class ResourceManagerAnlt:
    def __init__(
        self,
        testers: dict[str, "testers.GenericAnyTester"],
        port_identities: list["PortIdentity"],
        test_conf: "ModelAnlt",
        xoa_out: "TestSuitePipe",
    ) -> None:
        self.__port_identities: list["PortIdentity"] = port_identities
        self.__testers: dict[str, "testers.GenericAnyTester"] = testers
        self.__test_conf: "ModelAnlt" = test_conf
        self.__xoa_out: "TestSuitePipe" = xoa_out

    def send_statistics(self, data: Union[Dict, BaseModel]) -> None:
        self.__xoa_out.send_statistics(data)

    @property
    def xoa_out(self) -> "TestSuitePipe":
        return self.__xoa_out

    @property
    def tester(self) -> "testers.GenericAnyTester":
        return list(self.__testers.values())[0]

    @property
    def module(self) -> "FreyaModule":
        m = self.tester.modules.obtain(self.__port_identities[0].module_index)
        if isinstance(m, FreyaModuleIns):
            return m
        raise TypeError("Should be a freya module!")

    @property
    def port(self) -> "FreyaPort":
        return self.module.ports.obtain(self.__port_identities[0].port_index)

    @property
    def test_conf(self) -> "ModelAnlt":
        return self.__test_conf

    @property
    def test_types_conf(self) -> "TestTypesConfig":
        return self.__test_conf.test_types_config
