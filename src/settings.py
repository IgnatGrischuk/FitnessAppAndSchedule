from pydantic import BaseSettings


class Settings(BaseSettings):
    server_host: str = '127.0.0.1'
    server_port: int = '8000'

    angular_port: int = '4200'

    db_dialect: str = 'postgresql'
    db_username: str = 'postgres'
    db_password: str = '1234'
    db_host: str = 'localhost'
    db_port: str = '5432'
    db_database: str = 'fitness_app'

    adm_username: str = 'Ignat'
    adm_email: str = 'grischuk93@gmail.com'
    adm_password: str = '1234'

    timezone: str = 'MSK/Minsk'

    jwt_secret: str = ''
    jwt_algorithm: str = 'HS256'
    jwt_expires_s: int = 360000

    images_path = 'images'


settings = Settings(
    _env_file='../.env',
    _env_file_encoding='utf-8',
)
