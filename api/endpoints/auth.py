from core.config import settings
from models.pydantic.auth import (
    UserCreateByEmailModel,
    UserCreateByOauthModel,
    UserModel,
    UserLoginModel,
    PasswordResetModel,
    PassswordResetConfirmModel,
)
from services.auth.user_service import UserService
from database.db import get_session
from fastapi import APIRouter, Depends, status, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException
from services.auth.utils.password_utils import verify_password, generate_hash_password
from fastapi.responses import JSONResponse
from services.auth.dependencies import RefreshTokenBearer,  AccessTokenBearer, get_current_user, RoleChecker
from datetime import datetime
from services.auth.utils.token_utils import create_both_jwt_tokens, decode_token
from services.celery.celery_tasks import send_email
from database.redis import (
    add_token_to_blocklist_with_timestamp,
    get_token_from_blocklist,
    add_email_verification_cooldown,
    add_password_reset_email_cooldown,
)
from fastapi import BackgroundTasks
from services.auth.utils.url_safe_utils import create_url_safe_token, decode_url_safe_token
from services.errors.permission_errors import UserNotFound
import json
import time
from services.oauth.google_oauth import oauth


auth_router = APIRouter()
user_service = UserService()

current_protocol = "http://"
base_url = current_protocol + f"{settings.DOMAIN}"

verification_link = base_url + "/api/1.0/auth/verify/"
password_reset_link = base_url + "/api/1.0/auth/password_reset/"


# GOOGLE AUTH -----------------------
@auth_router.get("/google/login")
async def login(request: Request):
    redirect_uri = base_url + "/api/1.0/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@auth_router.get("/google/callback")
async def auth_google(request: Request, session: AsyncSession = Depends(get_session)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=400, detail="Google authentication failed")
    
    user_data = {
        "email": user_info['email'],
        "google_id": user_info['sub'],
        "name": user_info['name'],
        "is_verified": True,
    }
    user_exists = await user_service.user_exists(user_info['email'], session)

    if not user_exists:
        user = UserCreateByOauthModel(**user_data)
        new_user = await user_service.create_user_by_oauth(user, session)
    
    access_token, refresh_token = await create_both_jwt_tokens(user_data)

    return JSONResponse(
        content={
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token, 
        }
    )
    

#--------------------------------------------------------------


@auth_router.post("/signup", response_model=UserModel, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreateByEmailModel, background_tasks: BackgroundTasks, session: AsyncSession = Depends(get_session)):
    email = user_data.email

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists")

    new_user = await user_service.create_user_by_email(user_data, session)

    token = create_url_safe_token({
        "email": email,
    })

    body = {
        "link": verification_link + f"{token}",
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
async def login(user_data: UserLoginModel, session: AsyncSession = Depends(get_session)):
    email = user_data.email
    password = user_data.password

    user = await user_service.get_user_by_email(email, session)

    if user.google_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")

    if user is not None:
        password_valid = verify_password(password, user.password_hash)
    
        if password_valid:

            user_data={
                'email': user.email,
                'user_uid': str(user.uid),
                "role": user.role,
            }

            access_token, refresh_token = await create_both_jwt_tokens(user_data)

            return JSONResponse(
                content={
                    'message': 'Login successful',
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'user': {
                        'email': user.email,
                        'user_uid': str(user.uid),
                        "role": user.role,
                    }
                }
            )
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")


@auth_router.post("/refresh_token")
async def get_new_access_token(token_details:dict = Depends(RefreshTokenBearer())):
    expiry_timestamp = token_details['exp']

    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():

        old_access_token = await get_token_from_blocklist(f"session:{token_details['jti']}:access")
        if old_access_token:
            await add_token_to_blocklist_with_timestamp(old_access_token, expiry_timestamp)

        token_data = decode_token(token_details['token'])
        exp_time = token_data['exp']
        await add_token_to_blocklist_with_timestamp(token_details['token'], exp_time)

        user_data={
            'email': token_details['user']['email'],
            'user_uid': token_details['user']['user_uid'],
            "role": token_details['user']['role'],
        }

        access_token, refresh_token = await create_both_jwt_tokens(user_data)

        return JSONResponse(
            content={
                'access_token': access_token,
                'refresh_token': refresh_token,
            }
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been expired")


@auth_router.post("/logout")
async def logout(token_details:dict = Depends(AccessTokenBearer())):

    old_access_token = get_token_from_blocklist(f"session:{token_details['jti']}:access")
    if old_access_token:
        await add_token_to_blocklist_with_timestamp(old_access_token, token_details['exp'])

    return JSONResponse(
        content={
            "message": "Logout successful",
        },
        status_code=status.HTTP_200_OK,
    )

@auth_router.post("/me")
async def get_current_user(user = Depends(get_current_user), _: bool = Depends(RoleChecker(["admin"]))):
    return user


@auth_router.post("/resend_verification")
async def send_mail(background_tasks: BackgroundTasks, token_details:dict = Depends(AccessTokenBearer()), session: AsyncSession = Depends(get_session)):
    email = token_details['user']['email']

    blocklist_data = await get_token_from_blocklist(f"email_verification:{email}")
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
        "link": verification_link + f"{token}",
    }

    send_email.delay([email], "Email Verification", body, 'email_verification.html')

    await add_email_verification_cooldown(email)

    return JSONResponse(
        content = {
            "message" : "Email sent successfully",
        },
        status_code=status.HTTP_200_OK,
    )

@auth_router.get("/verify/{token}")
async def verify_user_account(token: str, session: AsyncSession = Depends(get_session)):
    token_data = decode_url_safe_token(token)

    user_email = token_data.get('email')

    if user_email:
        user = await user_service.get_user_by_email(user_email, session)

        if not user:
            raise UserNotFound()
        
        await user_service.update_user(user, {"is_verified": True}, session)

        return JSONResponse(
            content={
                "message": "Account verified",
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
async def password_reset(
    email_data: PasswordResetModel, 
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    email = email_data.email

    user_exists = await user_service.user_exists(email, session)

    if not user_exists:
        return JSONResponse(
            content = {
                "message" : "There is no account with this email!",
            },
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    blocklist_data = await get_token_from_blocklist(f"password_reset_email:{email}")
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
        "link": password_reset_link + f"{token}",
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
async def verify_user_account(
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