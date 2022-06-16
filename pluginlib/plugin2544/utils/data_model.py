from typing import Optional, Union
from pydantic import BaseModel, validator
from ipaddress import IPv4Address
from typing import List, Any
from enum import Enum
from decimal import Decimal
from .constants import ACTIVE_MODE


class Ports(BaseModel):
    """Post structure in Tester by Xmp"""

    id: str
    name: str
    reserved_by: str
    sync_status: str
    work_status: bool
    mac_address: str
    max_modifiers: int
    max_streams: int


class Modules(BaseModel):
    """Module structure in Tester by Xmp"""

    name: str
    reserved_by: str
    ports: List[Ports]


class ChassisInfo(BaseModel):
    host: str
    port: int
    password: str

    @validator("port")
    def port_range(cls, port):
        port = int(port)
        if port <= 0 or port >= 65535:
            raise ValueError("port should be between 0 and 65535")
        return port

    @validator("host")
    def validate_host(cls, host):
        addr = IPv4Address(host)
        # all_data = DataHandler().read()
        # for data in all_data.values():
        #     if data['host'] == host:
        #         raise ValueError(f'This chassis {host} has already been defined in your test configuration')
        return host


class TesterScheme(BaseModel):
    """Tester structure in DataSet"""

    id: str = ""
    is_connected = False
    host: str
    port: int
    password: str
    comment: str = ""
    name: str = ""
    module: List[Modules] = []

    @validator("id")
    def validate_id(cls, id):
        try:
            res = id.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            res = id
        return res

    @validator("port")
    def port_range(cls, port):
        port = int(port)
        if port <= 0 or port >= 65535:
            raise ValueError("port should be between 0 and 65535")
        return port

    @validator("host")
    def validate_host(cls, host):
        addr = IPv4Address(host)
        # all_data = DataHandler().read()
        # for data in all_data.values():
        #     if data['host'] == host:
        #         raise ValueError(f'This chassis {host} has already been defined in your test configuration')
        return host


class TesterData(BaseModel):
    """Tester structure return by Xmp"""

    id: str
    name: str
    comment: str = ""
    host: str
    port: int
    password: str
    reserved_by: str
    is_connected: bool
    modules: List[Optional[Modules]]


class UpdateFields(BaseModel):
    id: str
    name: str = ""
    comment: str = ""
    is_connected: bool


class UpdateConnectedStatus(BaseModel):
    id: str
    is_connected: bool


class TestSuit2544Model(BaseModel):
    """TestSuit 2544 structure"""

    host: str
    port: str
    xid: str
    east_port: str
    west_port: str
    reserved_by: str


class Message(BaseModel):
    mode: str
    action: str
    req_id: int = 0
    data: Any = None


class TaskObj(BaseModel):
    task: Any = None
    mode: str = ACTIVE_MODE
    action: str
    req_id: int = 0


class ErrorResponse(BaseModel):
    status: int
    message: str = "Fail"


class ID(BaseModel):
    id: str


class BinarySearchModel(BaseModel):
    port_id: str
    initial_rate: Decimal
    is_fast_search: bool = False
    use_pass_threshold: bool = False
    pass_threshold_pct: Decimal = Decimal("0.0")
    acceptable_loss_pct: Decimal = Decimal("0.0")
    min_rate: Decimal = Decimal("-1.1")
    max_rate: Decimal = Decimal("0.0")
    res_rate: Decimal = Decimal("-1.01")
    port_cap_rate_bps: Decimal
    statistics: List = []


class LatencyModel(BaseModel):
    port_id: str
    lower_bound: Decimal = Decimal("0.1")
    higher_bound: Decimal = Decimal("1.0")
    step: Decimal = Decimal("0.01")
    relative_to_throughput: bool = False
    throughput: Decimal = Decimal("0")
    port_cap_rate_bps: Decimal = Decimal("0")
    statistics: List = []


class FrameLossModel(BaseModel):
    port_id: str
    port_cap_rate_bps: Decimal = Decimal("0")
    lower_bound: Decimal = Decimal("0.1")
    higher_bound: Decimal = Decimal("1.0")
    step: Decimal = Decimal("0.01")
    use_pass_fail_criteria: bool = False
    acceptable_loss: Decimal = Decimal("0.0")
    statistics: List = []


class BackToBackModel(BaseModel):
    port_id: str
    port_cap_rate_bps: Decimal = Decimal("0")
    min_rate: Decimal = Decimal("0.1")
    max_rate: Decimal = Decimal("1.0")
    step: Decimal = Decimal("0.01")  # 1% of port tx rate
    burst_resolution: Decimal = Decimal("1")  # resolution = burst size resolution
    max_burst_size: Decimal = Decimal("0")
    statistics: List = []


class MessageSource(Enum):
    RESOURCE_POOL = 1
    FUNCTION_FATORY = 2
    STATISTICS = 3
    PLUGIN = 4


class MessageModel(BaseModel):
    mid: int = 0
    source: MessageSource = MessageSource.STATISTICS
    confirm_needed: bool = False
    message: Any


class MessageResponse(BaseModel):
    mid: int
    result: str


class ExecutorStatus(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    done: bool
    result: Any
    exception: Union[BaseException, None]
    cancel: bool
