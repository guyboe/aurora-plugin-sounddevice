import enum
import pathlib
from typing import Dict, List, Union

import pydantic

import pydantic_config

from .helpers import get_samplerate_func


class Config(pydantic_config.Settings):

    class Config:
        arbitrary_types_allowed = True

    class Input(pydantic.BaseModel):
        device: Union[int, str] = "default"
        samplerate: int = None

        _get_samplerate = pydantic.validator(
            "samplerate", always=True, allow_reuse=True)(get_samplerate_func("input")
        )

    class Output(pydantic.BaseModel):
        device: Union[int, str] = "default"
        samplerate: int = None

        _get_samplerate = pydantic.validator(
            "samplerate", always=True, allow_reuse=True)(get_samplerate_func("output")
        )

    class Queues(pydantic.BaseModel):

        class Config:
            use_enum_values = True
            arbitrary_types_allowed = True

        class Exchange(pydantic.BaseModel):

            class Config:
                use_enum_values = True

            class Name(pydantic_config.StrEnum):

                DETECT = enum.auto()
                SAY = enum.auto()
                PLAY = enum.auto()
                EXECUTE = enum.auto()

            class Type(pydantic_config.StrEnum):
                TOPIC = enum.auto()
                FANOUT = enum.auto()

            name: str
            proxy: str
            type: Type = Type.TOPIC.value
            durable: bool = False

        class Queue(pydantic.BaseModel):
            name: str
            exchange: str
            routing_key: str = "*"
            durable: bool = False
            exclusive: bool = False
            auto_delete: bool = True
            priority: int = None
            callback: str

        url: pydantic.AmqpDsn
        exchanges: Dict[Exchange.Name, Exchange] = pydantic.Field(default_factory=dict)
        queues: List[Queue] = pydantic.Field(default_factory=list)

    input: Input = pydantic.Field(default_factory=Input)
    output: Output = pydantic.Field(default_factory=Output)
    queues: Queues = pydantic.Field(default_factory=Queues)
    storage: pydantic.DirectoryPath = "/tmp/sounddevice"
    source: str = "sounddevice"
