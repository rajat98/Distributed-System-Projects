from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BankingOperationRequest(_message.Message):
    __slots__ = ["id", "type", "events"]
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    id: int
    type: str
    events: _containers.RepeatedCompositeFieldContainer[Event]
    def __init__(self, id: _Optional[int] = ..., type: _Optional[str] = ..., events: _Optional[_Iterable[_Union[Event, _Mapping]]] = ...) -> None: ...

class BankingOperationResponse(_message.Message):
    __slots__ = ["id", "recv"]
    ID_FIELD_NUMBER: _ClassVar[int]
    RECV_FIELD_NUMBER: _ClassVar[int]
    id: int
    recv: _containers.RepeatedCompositeFieldContainer[EventResult]
    def __init__(self, id: _Optional[int] = ..., recv: _Optional[_Iterable[_Union[EventResult, _Mapping]]] = ...) -> None: ...

class Event(_message.Message):
    __slots__ = ["id", "interface", "money"]
    ID_FIELD_NUMBER: _ClassVar[int]
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    MONEY_FIELD_NUMBER: _ClassVar[int]
    id: int
    interface: str
    money: int
    def __init__(self, id: _Optional[int] = ..., interface: _Optional[str] = ..., money: _Optional[int] = ...) -> None: ...

class EventResult(_message.Message):
    __slots__ = ["interface", "result", "balance"]
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    BALANCE_FIELD_NUMBER: _ClassVar[int]
    interface: str
    result: str
    balance: int
    def __init__(self, interface: _Optional[str] = ..., result: _Optional[str] = ..., balance: _Optional[int] = ...) -> None: ...
