from typing import Union, Optional, Dict

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel

from fastapi.security.utils import get_authorization_scheme_param
from jose import jwt, ExpiredSignatureError
from pydantic import BaseModel

from DB_Implementatins import db_additions_implementation, db_retrievals_implementation
from issues import client
from issues.client import ClientId
from servers_implementation import authentication

SECRET_KEY = "6hFiwU20LvHCMcZZlDiExQE_n9sSyyBomFiltXrxF9c"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
            self,
            tokenUrl: str,
            scheme_name: Optional[str] = None,
            scopes: Optional[Dict[str, str]] = None,
            auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.cookies.get("Authorization")  # changed to accept access token from httpOnly Cookie

        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


oauth2_cookie_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="token")


class TokenData(BaseModel):
    username: Union[str, None] = None


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(token: str = Depends(oauth2_cookie_scheme)):
    try:
        payload = jwt.decode(token, authentication.SECRET_KEY, algorithms=[authentication.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await db_retrievals_implementation.get_user_from_db(token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def check_permission_of_technician(user=Depends(get_current_user)):
    client_id = client.current_client
    if not client_id.client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Let us know which client you want to work with. You must enter the client number first."
        )
    if await db_additions_implementation.check_permission(user, client_id.client_id):
        return user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sorry! You cannot access this client.Try send a different client id."
        )
