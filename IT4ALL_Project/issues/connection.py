from pydantic import BaseModel

from issues.device import Device


class Connection(BaseModel):
    src_mac_address: str
    dst_mac_address: str
    protocol: str


class DevicesConnection(BaseModel):
    src_device: Device
    dst_device: Device
    protocol:str
