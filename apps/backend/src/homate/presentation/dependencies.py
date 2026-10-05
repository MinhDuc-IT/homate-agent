import jwt
from fastapi import Depends, HTTPException, Request, WebSocket
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from homate.infrastructure.tokens import decode_token

bearer = HTTPBearer(auto_error=False)


def get_household_service(request: Request): return request.app.state.household_service
def get_device_store(request: Request): return request.app.state.device_store
def get_ws_manager(request: Request): return request.app.state.ws_manager


def authenticated_user(token: str, service):
    try:
        payload = decode_token(token, expected="access")
    except jwt.PyJWTError:
        raise HTTPException(401, "Phiên đăng nhập không hợp lệ hoặc đã hết hạn.") from None
    user = service.get_user(str(payload.get("sub") or ""))
    if not user or not user["is_active"]:
        raise HTTPException(401, "Tài khoản không còn hoạt động.")
    return user


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), service=Depends(get_household_service)):
    if creds is None:
        raise HTTPException(401, "Vui lòng đăng nhập.", headers={"WWW-Authenticate": "Bearer"})
    return authenticated_user(creds.credentials, service)


def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin": raise HTTPException(403, "Chỉ quản trị viên được thay đổi cấu hình.")
    return user
