import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'default-dev-key'
    DATABASE_PATH = os.getenv('DATABASE_PATH') or 'database.db'
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') or 'jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
