from collections.abc import Callable
from hashlib import sha256
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from telecom_agent.ports.conversations import CustomerIdentityRepository


class UnauthorizedError(Exception):
    pass


def build_customer_authentication(
    customer_identities: CustomerIdentityRepository,
) -> Callable[..., UUID]:
    bearer = HTTPBearer(auto_error=False)

    def authenticate(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ) -> UUID:
        if credentials is None:
            raise UnauthorizedError

        token_hash = sha256(credentials.credentials.encode()).hexdigest()
        customer_id = customer_identities.find_customer_id(token_hash)
        if customer_id is None:
            raise UnauthorizedError
        return customer_id

    return authenticate
