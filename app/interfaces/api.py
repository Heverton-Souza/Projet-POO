from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import Config, load_config
from app.container import Container, Services, create_container
from app.domain.errors import AppError


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class CharacterRequest(BaseModel):
    name: str
    class_id: str = Field(alias="classId")
    race_id: str = Field(alias="raceId")


class AttributeRequest(BaseModel):
    attribute: str
    points: int


class ProgressRequest(BaseModel):
    amount: int = 1


class CombatActionRequest(BaseModel):
    action: str
    skill_id: str | None = Field(default=None, alias="skillId")


class QuantityRequest(BaseModel):
    quantity: int = 1


class RoleRequest(BaseModel):
    role: str


bearer = HTTPBearer(auto_error=False)


def create_app(config: Config | None = None) -> FastAPI:
    active_config = config or load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = create_container(active_config)
        yield
        app.state.container.close()

    app = FastAPI(
        title="Crônicas do Reino",
        description="API do sistema de RPG modelado com Clean Architecture, SOLID e padrões de projeto.",
        version="2.0.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, error: AppError) -> JSONResponse:
        return JSONResponse(status_code=error.status, content={"error": {"code": error.code, "message": error.message}})

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, _error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Confira os campos enviados.",
                }
            },
        )

    def get_container(request: Request) -> Container:
        return request.app.state.container

    def get_services(container: Annotated[Container, Depends(get_container)]) -> Services:
        return container.services

    def get_token(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> str | None:
        return credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None

    def get_current_user(
        services: Annotated[Services, Depends(get_services)],
        token: Annotated[str | None, Depends(get_token)],
    ) -> dict[str, Any]:
        return services.auth.authenticate(token)

    ServicesDep = Annotated[Services, Depends(get_services)]
    UserDep = Annotated[dict[str, Any], Depends(get_current_user)]
    TokenDep = Annotated[str | None, Depends(get_token)]

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
    def register(data: RegisterRequest, services: ServicesDep) -> dict[str, Any]:
        return services.auth.register(data.name, data.email, data.password)

    @app.post("/api/auth/login")
    def login(data: LoginRequest, services: ServicesDep) -> dict[str, Any]:
        return services.auth.login(data.email, data.password)

    @app.get("/api/auth/me")
    def me(user: UserDep) -> dict[str, Any]:
        return user

    @app.post("/api/auth/logout")
    def logout(services: ServicesDep, _user: UserDep, token: TokenDep) -> dict[str, str]:
        services.auth.logout(token)
        return {"message": "Sessão encerrada."}

    @app.get("/api/catalog/{resource}")
    def list_catalog(resource: str, services: ServicesDep) -> list[dict[str, Any]]:
        return services.admin.list_catalog(resource)

    @app.get("/api/characters")
    def list_characters(services: ServicesDep, user: UserDep) -> list[dict[str, Any]]:
        return services.characters.list_mine(user)

    @app.post("/api/characters", status_code=status.HTTP_201_CREATED)
    def create_character(data: CharacterRequest, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.use_cases.create_character.execute(user, data.name, data.class_id, data.race_id)

    @app.get("/api/characters/{character_id}")
    def get_character(character_id: str, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.characters.get(user, character_id)

    @app.patch("/api/characters/{character_id}/attributes")
    def distribute_attribute(
        character_id: str, data: AttributeRequest, services: ServicesDep, user: UserDep
    ) -> dict[str, Any]:
        return services.characters.distribute_attribute(user, character_id, data.attribute, data.points)

    @app.post("/api/characters/{character_id}/recover")
    def recover_character(character_id: str, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.characters.recover(user, character_id)

    @app.get("/api/characters/{character_id}/missions/available")
    def available_missions(character_id: str, services: ServicesDep, user: UserDep) -> list[dict[str, Any]]:
        return services.missions.list_available(user, character_id)

    @app.get("/api/characters/{character_id}/missions")
    def character_missions(character_id: str, services: ServicesDep, user: UserDep) -> list[dict[str, Any]]:
        return services.missions.list_mine(user, character_id)

    @app.post(
        "/api/characters/{character_id}/missions/{mission_id}/accept",
        status_code=status.HTTP_201_CREATED,
    )
    def accept_mission(
        character_id: str, mission_id: str, services: ServicesDep, user: UserDep
    ) -> dict[str, Any]:
        return services.use_cases.accept_mission.execute(user, character_id, mission_id)

    @app.patch("/api/mission-progress/{progress_id}")
    def update_mission(
        progress_id: str, data: ProgressRequest, services: ServicesDep, user: UserDep
    ) -> dict[str, Any]:
        return services.missions.update(user, progress_id, data.amount)

    @app.post("/api/mission-progress/{progress_id}/complete")
    def complete_mission(progress_id: str, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.missions.complete(user, progress_id)

    @app.post("/api/mission-progress/{progress_id}/cancel")
    def cancel_mission(progress_id: str, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.missions.cancel(user, progress_id)

    @app.get("/api/characters/{character_id}/inventory")
    def inventory(character_id: str, services: ServicesDep, user: UserDep) -> list[dict[str, Any]]:
        return services.inventory.list(user, character_id)

    @app.post("/api/characters/{character_id}/inventory/{item_id}/equip")
    def equip_item(character_id: str, item_id: str, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.inventory.equip(user, character_id, item_id)

    @app.post("/api/characters/{character_id}/inventory/{item_id}/unequip")
    def unequip_item(character_id: str, item_id: str, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.inventory.unequip(user, character_id, item_id)

    @app.post("/api/characters/{character_id}/inventory/{item_id}/use")
    def use_item(character_id: str, item_id: str, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.inventory.use(user, character_id, item_id)

    @app.delete("/api/characters/{character_id}/inventory/{item_id}")
    def remove_item(
        character_id: str,
        item_id: str,
        services: ServicesDep,
        user: UserDep,
        quantity: Annotated[int, Query(gt=0)] = 1,
    ) -> dict[str, Any] | None:
        return services.inventory.remove(user, character_id, item_id, quantity)

    @app.get("/api/characters/{character_id}/combats")
    def combats(character_id: str, services: ServicesDep, user: UserDep) -> list[dict[str, Any]]:
        return services.use_cases.perform_combat.list(user, character_id)

    @app.post("/api/characters/{character_id}/combats/{enemy_id}", status_code=status.HTTP_201_CREATED)
    def start_combat(character_id: str, enemy_id: str, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.use_cases.perform_combat.start(user, character_id, enemy_id)

    @app.post("/api/combats/{combat_id}/actions")
    def combat_action(
        combat_id: str, data: CombatActionRequest, services: ServicesDep, user: UserDep
    ) -> dict[str, Any]:
        return services.use_cases.perform_combat.execute(user, combat_id, data.action, data.skill_id)

    @app.get("/api/characters/{character_id}/history")
    def history(character_id: str, services: ServicesDep, user: UserDep) -> list[dict[str, Any]]:
        return services.history.list(user, character_id)

    @app.get("/api/admin/users")
    def admin_users(services: ServicesDep, user: UserDep) -> list[dict[str, Any]]:
        return services.admin.list_users(user)

    @app.patch("/api/admin/users/{user_id}/role")
    def update_role(user_id: str, data: RoleRequest, services: ServicesDep, user: UserDep) -> dict[str, Any]:
        return services.admin.update_user_role(user, user_id, data.role)

    @app.get("/api/admin/characters")
    def admin_characters(services: ServicesDep, user: UserDep) -> list[dict[str, Any]]:
        return services.admin.list_characters(user)

    @app.post("/api/admin/characters/{character_id}/inventory/{item_id}")
    def grant_item(
        character_id: str,
        item_id: str,
        services: ServicesDep,
        user: UserDep,
        data: Annotated[QuantityRequest, Body()] = QuantityRequest(),
    ) -> dict[str, Any]:
        return services.inventory.grant(user, character_id, item_id, data.quantity)

    @app.post("/api/admin/catalog/{resource}", status_code=status.HTTP_201_CREATED)
    def create_catalog(
        resource: str, data: dict[str, Any], services: ServicesDep, user: UserDep
    ) -> dict[str, Any]:
        return services.admin.create(user, resource, data)

    @app.put("/api/admin/catalog/{resource}/{item_id}")
    def update_catalog(
        resource: str, item_id: str, data: dict[str, Any], services: ServicesDep, user: UserDep
    ) -> dict[str, Any]:
        return services.admin.update(user, resource, item_id, data)

    @app.delete("/api/admin/catalog/{resource}/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_catalog(resource: str, item_id: str, services: ServicesDep, user: UserDep) -> Response:
        services.admin.remove(user, resource, item_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    public_directory = Path(__file__).resolve().parents[2] / "public"
    app.mount("/", StaticFiles(directory=public_directory, html=True), name="public")
    return app
