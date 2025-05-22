from models.db.users import User
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from models.pydantic.auth import UserCreateByOauthModel, UserCreateByEmailModel
from .utils.password_utils import generate_hash_password
from services.errors.permission_errors import UserNotFound

class UserService:
    async def get_user_by_email(self, email: str, session: AsyncSession, raise_error: bool = False) -> User:
        statement = select(User).where(User.email == email)

        result = await session.exec(statement)

        user = result.first()

        if user is None and raise_error:
            raise UserNotFound()

        return user
    
    async def user_exists(self, email: str, session: AsyncSession) -> bool:
        user = await self.get_user_by_email(email, session)

        return False if user is None else True
    
    async def create_user_by_email(self, user_data: UserCreateByEmailModel, session: AsyncSession) -> User:
        user_data_dict = user_data.model_dump()

        new_user = User(**user_data_dict)

        new_user.password_hash = generate_hash_password(user_data_dict['password'])

        new_user.role = "user"

        session.add(new_user)

        await session.commit()

        return new_user
    
    async def create_user_by_oauth(self, user_data: UserCreateByOauthModel, session: AsyncSession) -> User:
        user_data_dict = user_data.model_dump()

        new_user = User(**user_data_dict)

        new_user.role = "user"

        session.add(new_user)

        await session.commit()

        return new_user
    
    async def update_user(self, user: User, user_data: dict, session: AsyncSession):

        for key, value in user_data.items():
            setattr(user, key, value)

        await session.commit()

        return user
    

user_service = UserService()