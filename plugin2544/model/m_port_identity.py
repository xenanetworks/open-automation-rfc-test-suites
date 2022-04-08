from pydantic import BaseModel, NonNegativeInt


class PortIdentity(BaseModel):
    chassis_id: str
    chassis_index: int = 0
    module_index: NonNegativeInt
    port_index: NonNegativeInt

    def change_chassis_index(self, chassis_index: int):
        self.chassis_index = chassis_index
    @property
    def identity(self):
        return f"{self.chassis_index}-{self.module_index}-{self.port_index}"