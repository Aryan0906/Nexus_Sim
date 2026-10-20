"""JWT-based authentication and workspace authorization for NexusSim gateway.

Issues short-lived JWT tokens on login and validates workspace-scoped access
for all protected endpoints. In production, swap the in-memory user store for
OIDC/OAuth2 (Keycloak, Auth0, Azure AD) and persist workspaces in PostgreSQL.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get("NEXUSSIM_JWT_SECRET", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("NEXUSSIM_JWT_EXPIRE_MIN", "60"))

# In-memory user store (replace with DB in production)
# username -> {password_hash, workspaces: [workspace_id, ...], role: "admin"|"editor"|"viewer"}
USERS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "password": "admin",  # plaintext only for dev; use bcrypt/argon2 in prod
        "workspaces": ["ws_default", "ws_acme"],
        "role": "admin",
    },
    "viewer": {
        "password": "viewer",
        "workspaces": ["ws_default"],
        "role": "viewer",
    },
}

# Workspace registry (replace with DB in production)
# workspace_id -> {name, owner, members: [user_id, ...], plan}
WORKSPACES: Dict[str, Dict[str, Any]] = {
    "ws_default": {
        "name": "Default Workspace",
        "owner": "admin",
        "members": ["admin", "viewer"],
        "plan": "team",
    },
    "ws_acme": {
        "name": "Acme Consulting",
        "owner": "admin",
        "members": ["admin"],
        "plan": "enterprise",
    },
}

security = HTTPBearer()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[int] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = time.time() + (expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user against the in-memory store."""
    user = USERS.get(username)
    if not user or user["password"] != password:
        return None
    return {
        "username": username,
        "workspaces": user["workspaces"],
        "role": user["role"],
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """Dependency to get the current authenticated user."""
    token = credentials.credentials
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    user = USERS.get(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return {"username": username, "workspaces": user["workspaces"], "role": user["role"]}


def require_workspace_access(workspace_id: str):
    """Dependency factory: require the current user to have access to a workspace."""

    def _check(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if workspace_id not in user["workspaces"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User '{user['username']}' has no access to workspace '{workspace_id}'",
            )
        return user

    return _check


def require_role(allowed_roles: list):
    """Dependency factory: require the current user to have one of the allowed roles."""

    def _check(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role one of {allowed_roles}, got '{user['role']}'",
            )
        return user

    return _check


def list_user_workspaces(user: Dict[str, Any]) -> list:
    """Return workspace details for a user's accessible workspaces."""
    return [
        {
            "workspace_id": wid,
            "name": WORKSPACES[wid]["name"],
            "owner": WORKSPACES[wid]["owner"],
            "plan": WORKSPACES[wid]["plan"],
        }
        for wid in user["workspaces"]
        if wid in WORKSPACES
    ]


def create_workspace(workspace_id: str, name: str, owner: str) -> Dict[str, Any]:
    """Create a new workspace."""
    if workspace_id in WORKSPACES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workspace '{workspace_id}' already exists",
        )
    WORKSPACES[workspace_id] = {
        "name": name,
        "owner": owner,
        "members": [owner],
        "plan": "team",
    }
    # Grant owner access
    owner_user = USERS.get(owner)
    if owner_user and workspace_id not in owner_user["workspaces"]:
        owner_user["workspaces"].append(workspace_id)
    return WORKSPACES[workspace_id]
