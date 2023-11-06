from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BankingOperationRequest(_message.Message):
    __slots__ = ["id", "type", "customer_requests"]
    ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CUSTOMER_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    id: int
    type: str
    customer_requests: _containers.RepeatedCompositeFieldContainer[CustomerRequest]
    def __init__(self, id: _Optional[int] = ..., type: _Optional[str] = ..., customer_requests: _Optional[_Iterable[_Union[CustomerRequest, _Mapping]]] = ...) -> None: ...

class BankingOperationResponse(_message.Message):
    __slots__ = ["event_result"]
    EVENT_RESULT_FIELD_NUMBER: _ClassVar[int]
    event_result: _containers.RepeatedCompositeFieldContainer[EventResult]
    def __init__(self, event_result: _Optional[_Iterable[_Union[EventResult, _Mapping]]] = ...) -> None: ...

class CustomerRequest(_message.Message):
    __slots__ = ["customer_request_id", "interface", "logical_clock", "money"]
    CUSTOMER_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    LOGICAL_CLOCK_FIELD_NUMBER: _ClassVar[int]
    MONEY_FIELD_NUMBER: _ClassVar[int]
    customer_request_id: int
    interface: str
    logical_clock: int
    money: int
    def __init__(self, customer_request_id: _Optional[int] = ..., interface: _Optional[str] = ..., logical_clock: _Optional[int] = ..., money: _Optional[int] = ...) -> None: ...

class EventResult(_message.Message):
    __slots__ = ["id", "customer_request_id", "type", "logical_clock", "interface", "comment"]
    ID_FIELD_NUMBER: _ClassVar[int]
    CUSTOMER_REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    LOGICAL_CLOCK_FIELD_NUMBER: _ClassVar[int]
    INTERFACE_FIELD_NUMBER: _ClassVar[int]
    COMMENT_FIELD_NUMBER: _ClassVar[int]
    id: int
    customer_request_id: int
    type: str
    logical_clock: int
    interface: str
    comment: str
    def __init__(self, id: _Optional[int] = ..., customer_request_id: _Optional[int] = ..., type: _Optional[str] = ..., logical_clock: _Optional[int] = ..., interface: _Optional[str] = ..., comment: _Optional[str] = ...) -> None: ...
