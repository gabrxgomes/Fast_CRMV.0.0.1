from config import db
from datetime import datetime
from sqlalchemy.sql import func



class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    sector = db.Column(db.String(100), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    #created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Data de criação do usuário
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    manager = db.relationship('User', remote_side=[id], backref='subordinates')

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    sector = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))

    # Novos campos adicionados
    meeting_date = db.Column(db.Date)  # Data da reunião
    video_link = db.Column(db.String(255))  # Link da reunião (Meet)
    comments = db.Column(db.Text)  # Comentários adicionais
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Data de criação do cliente
    image_url = db.Column(db.String(255), nullable=True)

    users = db.relationship('User', secondary='user_clients', backref='clients')

class UserClient(db.Model):
    __tablename__ = 'user_clients'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), primary_key=True)


# Fast_CRM/models.py

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
