from dataclasses import dataclass
from typing import Union
from fern.proto.stream import RPCStream, RPCFrame


@dataclass(frozen=True)
class Request:
    id: int
    name: str
    args: dict

    def to_json(self):
        return {"name": self.name, "args": self.args}

    async def send(self, s: RPCStream):
        await s.send(self.id, self.to_json(), is_stream=False)


@dataclass(frozen=True)
class StreamContent:
    id: int
    content: Union[dict, bytes]
    is_eos: bool = False
    is_error: bool = False

    async def send(self, s: RPCStream):
        await s.send(self.id,
                     self.content,
                     is_eos=self.is_eos,
                     is_error=self.is_error,
                     is_stream=True)


@dataclass(frozen=True)
class Response:
    id: int
    content: Union[dict, bytes]
    is_error: bool = False

    async def send(self, s: RPCStream):
        await s.send(self.id,
                     self.content,
                     is_error=self.is_error,
                     is_eos=False,
                     is_stream=False)


def decode_frame(frame: RPCFrame, is_server: bool) -> Union[Request, StreamContent, Response]:
    if is_server:
        return Request(
            id=frame.request_id,
            name=frame.data['name'],
            args=frame.data['args'],
        )
    if frame.is_stream:
        return StreamContent(
            id=frame.request_id,
            content=frame.data,
            is_eos=frame.is_eos,
            is_error=frame.is_error,
        )
    else:
        return Response(
            id=frame.request_id,
            content=frame.data,
            is_error=frame.is_error,
        )
