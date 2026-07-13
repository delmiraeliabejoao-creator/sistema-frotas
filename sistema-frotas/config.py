import os

class Config:
    SECRET_KEY = "chave_secreta_sistema_frota_2026"
    SQLALCHEMY_DATABASE_URI = "sqlite:///sistema_frota.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
