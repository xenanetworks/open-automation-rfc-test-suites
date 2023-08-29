from pydantic import BaseModel
from .models.module_config import ModuleConfiguration
# from .models.port_config import PortConfiguration
from .models.test_types_config import TestTypesConfig


class ModelAnlt(BaseModel):
    module_config: ModuleConfiguration
    # port_config: PortConfiguration
    test_types_config: TestTypesConfig
