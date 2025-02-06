from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)

class Analytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    metric = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Integer, nullable=False)
