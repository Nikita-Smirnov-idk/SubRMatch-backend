from itsdangerous import URLSafeTimedSerializer
from core.config import settings
import logging


serializer = URLSafeTimedSerializer(
    secret_key=settings.JWT_SECRET_KEY,
    salt="email-configuration"
)


def create_url_safe_token(data: dict):
    token = serializer.dumps(data)

    return token


def decode_url_safe_token(token:str, max_age:int = 86400):
    try:
        token_data = serializer.loads(token, max_age=max_age)

        return token_data
    
    except Exception as ex:
        logging.error(str(ex))