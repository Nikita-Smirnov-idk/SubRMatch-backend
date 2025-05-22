from core.config import settings
from models.pydantic.auth import (
    UserCreateByEmailModel,
    UserCreateByOauthModel,
    UserModel,
    UserLoginModel,
    PasswordResetModel,
    PassswordResetConfirmModel,
)
from models.pydantic.validators.auth_validators import validate_uri
from services.auth.user_service import user_service
from database.db import get_session
from fastapi import APIRouter, Depends, status, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException
from services.auth.utils.password_utils import verify_password, generate_hash_password
from fastapi.responses import JSONResponse
from services.auth.dependencies import RefreshTokenBearer,  AccessTokenBearer, get_current_user, RoleChecker
from datetime import datetime, timezone
from services.auth.utils.token_utils import create_both_jwt_tokens
from services.celery.celery_tasks import send_email
from database.redis import (
    get_token_from_storage,
    add_email_verification_cooldown,
    add_password_reset_email_cooldown,
    save_jwt_tokens_with_state,
    delete_from_storage,
    revoke_user_tokens,
)
from fastapi import BackgroundTasks
from services.auth.utils.url_safe_utils import create_url_safe_token, decode_url_safe_token
from services.errors.permission_errors import UserNotFound
import json
import time
from services.oauth.google_oauth import oauth
from api.utils import limiter
from middleware.main_middleware import origins
import uuid
from starlette.responses import RedirectResponse


auth_router = APIRouter()

current_protocol = "http://"
base_url = current_protocol + f"{settings.DOMAIN}"

verification_link = base_url + "/api/1.0/auth/verify/"
password_reset_link = base_url + "/api/1.0/auth/password_reset/"


# GOOGLE AUTH -----------------------
@auth_router.get("/google/login")
@limiter.limit("4/second")
async def login(request: Request, redirect_uri: str = None):
    request.session["redirect_uri"] = validate_uri(redirect_uri)

    google_redirect_uri = base_url + "/api/1.0/auth/google/callback"
    return await oauth.google.authorize_redirect(request, google_redirect_uri)


@auth_router.get("/google/callback")
@limiter.limit("4/second")
async def auth_google(request: Request, session: AsyncSession = Depends(get_session)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google authentication failed")
    
    user_data = {
        "email": user_info['email'],
        "google_id": user_info['sub'],
        "name": user_info['name'],
        "is_verified": True,
    }
    user = await user_service.get_user_by_email(user_info['email'], session)

    if user and user.password_hash is not None:
        if not user.is_verified:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verify your account to login via Google, this account is already registered not via Google")

        if user.is_verified and user.google_id is None:
            data = {
                'google_id': user_info['sub']
            }
            await user_service.update_user(user, data, session)
        

    if user is None:
        user = UserCreateByOauthModel(**user_data)
        user = await user_service.create_user_by_oauth(user, session)

    user_data = user.get_safe_as_dict()
    
    access_token, refresh_token = await create_both_jwt_tokens(user_data, session)

    frontend_redirect = request.session.get("redirect_uri")
    if not frontend_redirect:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No redirect_uri in session")

    # Сохранение токенов в Redis
    state = str(uuid.uuid4())
    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

    await save_jwt_tokens_with_state(state, json.dumps(token_data))
    
    return RedirectResponse(f"{frontend_redirect}?state={state}")


# Эндпоинт для получения токенов
@auth_router.get("/oauth/tokens")
@limiter.limit("4/second")
async def get_tokens(request: Request, state: str):
    tokens_key = f"tokens:{state}"
    token_data = await get_token_from_storage(tokens_key)
    
    if not token_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state")
    
    tokens = json.loads(token_data)

    await delete_from_storage(tokens_key)  # Удаляем после получения
    return JSONResponse({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer"
    })

#--------------------------------------------------------------


@auth_router.post("/signup", response_model=UserModel, status_code=status.HTTP_201_CREATED)
@limiter.limit("4/second")
async def signup(request: Request, user_data: UserCreateByEmailModel, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    email = user_data.email

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists")

    new_user = await user_service.create_user_by_email(user_data, session)

    token = create_url_safe_token({
        "email": email,
    })

    body = {
        "link": user_data.redirect_uri + f"{token}",
    }

    send_email.delay([email], "Email Verification", body, 'email_verification.html')

    await add_email_verification_cooldown(email)

    return JSONResponse(
        content = {
            "message" : "Account created! Email sent successfully",
        },
        status_code=status.HTTP_201_CREATED,
    )



@auth_router.post("/login", response_model=UserLoginModel)
@limiter.limit("4/second")
async def login(request: Request, user_data: UserLoginModel, session: AsyncSession = Depends(get_session)):
    email = user_data.email
    password = user_data.password
    
    user = await user_service.get_user_by_email(email, session)

    if user.google_id and (user.password_hash is None):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")

    if user is not None:
        password_valid = verify_password(password, user.password_hash)
    
        if password_valid:

            user_data=user.get_safe_as_dict()

            access_token, refresh_token = await create_both_jwt_tokens(user_data, session)
            return JSONResponse(
                content={
                    'message': 'Login successful',
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                }
            )
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")


@auth_router.post("/refresh_token")
@limiter.limit("4/second")
async def get_new_access_token(request: Request, token_details: dict = Depends(RefreshTokenBearer()), session: AsyncSession = Depends(get_session)):
    user = await user_service.get_user_by_email(token_details['user']['email'], session)

    access_jti = await get_token_from_storage(f"{user.uid}:refresh_to_access:{token_details['jti']}")
    name = f"{user.uid}:access:{access_jti}"

    old_access_token = await get_token_from_storage(f"{user.uid}:access:{access_jti}")
    if old_access_token:
        await delete_from_storage(f"{user.uid}:access:{access_jti}")

    await delete_from_storage(f"{user.uid}:refresh:{token_details['jti']}")
    await delete_from_storage(f"{user.uid}:refresh_to_access:{token_details['jti']}")

    access_token, refresh_token = await create_both_jwt_tokens(token_details['user'], session)

    return JSONResponse(
        content={
            'access_token': access_token,
            'refresh_token': refresh_token,
        }
    )


@auth_router.post("/logout")
@limiter.limit("4/second")
async def logout(request: Request, token_details: dict = Depends(RefreshTokenBearer()), session: AsyncSession = Depends(get_session)):
    user = await user_service.get_user_by_email(token_details['user']['email'], session)

    access_jti = await get_token_from_storage(f"{user.uid}:refresh_to_access:{token_details['jti']}")

    old_access_token = await get_token_from_storage(f"{user.uid}:access:{access_jti}")
    if old_access_token:
        await delete_from_storage(f"{user.uid}:access:{access_jti}")

    await delete_from_storage(f"{user.uid}:refresh:{token_details['jti']}")
    await delete_from_storage(f"{user.uid}:refresh_to_access:{token_details['jti']}")

    return JSONResponse(
        content={
            "message": "Logout successful",
        },
        status_code=status.HTTP_200_OK,
    )

@auth_router.post("/me")
@limiter.limit("2/second")
async def get_current_user(request: Request, user = Depends(get_current_user), _: bool = Depends(RoleChecker(["user","admin"]))):
    return JSONResponse(
        content={
            "user": user.role,
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.post("/resend_verification")
@limiter.limit("2/second")
async def send_mail(request: Request, background_tasks: BackgroundTasks, redirect_uri: str = None, token_details:dict = Depends(AccessTokenBearer()), session: AsyncSession = Depends(get_session)):
    redirect_uri = validate_uri(redirect_uri)
    email = token_details['user']['email']

    blocklist_data = await get_token_from_storage(f"email_verification:{email}")
    if blocklist_data:
        data = json.loads(blocklist_data)
        last_sent_time = data["time"]
        current_time = time.time()
        if current_time - last_sent_time < settings.MAIL_VERIFICATION_COOLDOWN:
            remaining_time = int(settings.MAIL_VERIFICATION_COOLDOWN - (current_time - last_sent_time))
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {remaining_time} seconds before resending."
            )

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        user = await user_service.get_user_by_email(email, session)
        if user.is_verified:
            return JSONResponse(
                content = {
                    "message" : "You are already verified!",
                },
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

    token = create_url_safe_token({
        "email": email,
    })

    body = {
        "link": redirect_uri + f"{token}",
    }

    send_email.delay([email], "Email Verification", body, 'email_verification.html')

    await add_email_verification_cooldown(email)

    return JSONResponse(
        content = {
            "message" : "Email sent successfully",
        },
        status_code=status.HTTP_200_OK,
    )

@auth_router.post("/verify/{token}")
@limiter.limit("2/second")
async def verify_user_account(request: Request, token: str, session: AsyncSession = Depends(get_session)):

    token_data = decode_url_safe_token(token)

    user_email = token_data.get('email')

    if user_email:
        user = await user_service.get_user_by_email(user_email, session)

        if not user:
            raise UserNotFound()
        
        await user_service.update_user(user, {"is_verified": True}, session)

        return JSONResponse(
            content={
                "message": "Account verified successfully",
            },
            status_code=status.HTTP_200_OK,
        )
    
    return JSONResponse(
        content={
            "message": "Error occured during verification",
        },
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@auth_router.post('/password_reset')
@limiter.limit("2/second")
async def password_reset(
    request: Request,
    data: PasswordResetModel,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    redirect_uri = data.redirect_uri
    
    email = data.email

    user_exists = await user_service.user_exists(email, session)

    if not user_exists:
        return JSONResponse(
            content = {
                "message" : "There is no account with this email!",
            },
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    blocklist_data = await get_token_from_storage(f"password_reset_email:{email}")
    if blocklist_data:
        data = json.loads(blocklist_data)
        last_sent_time = data["time"]
        current_time = time.time()
        if current_time - last_sent_time < settings.MAIL_VERIFICATION_COOLDOWN:
            remaining_time = int(settings.MAIL_VERIFICATION_COOLDOWN - (current_time - last_sent_time))
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {remaining_time} seconds before resending."
            )

    token = create_url_safe_token({
        "email": email,
    })

    body = {
        "link": redirect_uri + f"{token}",
    }

    send_email.delay([email], "Reset your password", body, 'password_reset.html')

    await add_password_reset_email_cooldown(email)

    return JSONResponse(
        content = {
            "message" : "Email sent successfully",
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.post("/password_reset_confirm/{token}")
@limiter.limit("2/second")
async def passsword_reset_confirm(
    request: Request,
    token: str,
    passwords: PassswordResetConfirmModel,
    session: AsyncSession = Depends(get_session)
):
    if passwords.new_password != passwords.confirm_new_password:
        raise HTTPException(
            detail="Passwords do not match!",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    token_data = decode_url_safe_token(token)

    user_email = token_data.get('email')

    if user_email:
        user = await user_service.get_user_by_email(user_email, session)

        if not user:
            raise UserNotFound()
        
        password_hash = generate_hash_password(passwords.new_password)

        await user_service.update_user(user, {"password_hash": password_hash}, session)

        await revoke_user_tokens(user.uid)

        return JSONResponse(
            content={
                "message": "Password reset successfully",
            },
            status_code=status.HTTP_200_OK,
        )
    
    return JSONResponse(
        content={
            "message": "Error occured during password reset!",
        },
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )