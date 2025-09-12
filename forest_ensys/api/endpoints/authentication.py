# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from forest_ensys import schemas, crud, model
from forest_ensys.api import deps
from forest_ensys.core import security, settings

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
def login(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> schemas.Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = crud.user.authenticate(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password!",
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = security.create_access_token(user.id, expires_delta=access_token_expires)
    return schemas.Token(access_token=token, token_type="bearer")


@router.post(
    "/register",
    response_model=schemas.User,
    responses={409: {"description": "User with same name already exists."}},
)
def register(
    request: schemas.UserCreate, db: Session = Depends(deps.get_db)
) -> schemas.User:
    """
    Create a new user
    """
    user = crud.user.get_by_username(db, username=request.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with that username already exists!",
        )

    user = crud.user.create(db, obj_in=request)

    return user


@router.get("/test-token", response_model=schemas.User)
def test_token(
    current_user: model.User = Depends(deps.get_current_user),
) -> schemas.User:
    """
    Test access token
    """
    return current_user
