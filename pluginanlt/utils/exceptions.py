from typing import Type


class NotFreyaModuleError(Exception):
    def __init__(self, module_index: int, module: Type) -> None:
        self.msg = f"Module {module_index} is a {module.__name__}, not a Freya module."
        super().__init__(self.msg)


class NotFreyaPortError(Exception):
    def __init__(self, module_index: int, port_index: int, port_type: Type) -> None:
        self.msg = f"Module {module_index}/{port_index} is a {port_type.__name__}, not a Freya port."
        super().__init__(self.msg)
