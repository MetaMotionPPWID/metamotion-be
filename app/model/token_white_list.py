from datetime import datetime
from app.extension import db


class TokenWhiteList(db.Model):
    __tablename__ = "tokens_white_list"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user = db.relationship("User", back_populates="tokens")

    def __repr__(self):
        return f"<Token {self.jti}>"

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
