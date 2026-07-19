from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        if not any(character.isupper() for character in password):
            raise ValueError("Şifre en az bir büyük harf içermelidir")
        if not any(character.islower() for character in password):
            raise ValueError("Şifre en az bir küçük harf içermelidir")
        if not any(not character.isalnum() and not character.isspace() for character in password):
            raise ValueError("Şifre en az bir özel karakter içermelidir")
        return password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr

    model_config = {"from_attributes": True}
