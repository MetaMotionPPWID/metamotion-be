from app.constants.default_roles import DefaultRoles
from app.extension import db
from app.model.association import users_roles


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    users = db.relationship("User", secondary=users_roles, back_populates="roles")

    @classmethod
    def get_role_by_name(cls, role_name):
        return cls.query.filter_by(name=role_name).first()

    @classmethod
    def check_default_roles_exist(cls):
        for role in DefaultRoles:
            if not cls.query.filter_by(name=role.value).first():
                return False
        return True

    @classmethod
    def create_default_roles(cls):
        for role in DefaultRoles:
            role_value = role.value
            if not cls.query.filter_by(name=role_value).first():
                db.session.add(cls(name=role_value))
        db.session.commit()
