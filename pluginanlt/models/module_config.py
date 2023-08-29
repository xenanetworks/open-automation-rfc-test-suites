from pydantic import BaseModel


class ModuleConfiguration(BaseModel):
    description: str
    media_type: str
    port_count: int
    port_speed: str


class FixedModuleConfiguration(ModuleConfiguration):
    model: str
    serial_number: str
    firmware_version: str
    temperature: int
