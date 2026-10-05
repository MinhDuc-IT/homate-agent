from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Action = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HomeInput(Input):
    name: Name
    timezone: str = "Asia/Ho_Chi_Minh"


class RoomInput(Input):
    name: Name
    home_id: UUID


class DeviceInput(RoomInput):
    room_id: UUID
    kind: Literal["light", "fan", "climate", "plug", "lock", "curtain", "sensor", "other"]
    capabilities: list[Action] = Field(default_factory=list, max_length=50)


class StepInput(Input):
    device_id: UUID
    action: Action
    parameters: dict = Field(default_factory=dict)


class SceneInput(RoomInput):
    is_enabled: bool = True
    steps: list[StepInput] = Field(default_factory=list, max_length=100)


def catalog_router(service_dependency):
    router = APIRouter(prefix="/api")

    def register(kind, schema):
        # Separate function scope keeps each endpoint's schema and resource bound.
        def listing(home_id: UUID | None = None, service=Depends(service_dependency, scope="function")):
            return service.list(kind, home_id)

        def detail(identifier: UUID, service=Depends(service_dependency, scope="function")):
            return service.get(kind, identifier)

        def create(body: schema, service=Depends(service_dependency, scope="function")):
            return service.save(kind, body.model_dump())

        def replace(identifier: UUID, body: schema, service=Depends(service_dependency, scope="function")):
            return service.save(kind, body.model_dump(), identifier)

        def remove(identifier: UUID, service=Depends(service_dependency, scope="function")):
            service.delete(kind, identifier)
            return Response(status_code=204)

        for path, endpoint, methods, code in [
            (f"/{kind}", listing, ["GET"], 200),
            (f"/{kind}/{{identifier}}", detail, ["GET"], 200),
            (f"/{kind}", create, ["POST"], 201),
            (f"/{kind}/{{identifier}}", replace, ["PUT"], 200),
            (f"/{kind}/{{identifier}}", remove, ["DELETE"], 204),
        ]:
            router.add_api_route(path, endpoint, methods=methods, status_code=code,
                                 tags=[kind], name=f"{kind}_{endpoint.__name__}")

    for kind, schema in [("homes", HomeInput), ("rooms", RoomInput), ("devices", DeviceInput), ("scenes", SceneInput)]:
        register(kind, schema)
    return router
