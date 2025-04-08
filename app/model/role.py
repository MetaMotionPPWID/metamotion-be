from constants.default_roles import DefaultRoles
from extension import db
from model.association import users_roles


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    users = db.relationship(
        'User',
        secondary=users_roles,
        back_populates='roles')

    @classmethod
    def get_role_by_name(cls, role_name):
        return cls.query.filter_by(name=role_name).first()

    @classmethod
    def create_default_roles(cls):
        for role in DefaultRoles:
            role_value = role.value
            if not cls.query.filter_by(name=role_value).first():
                db.session.add(cls(name=role_value))
        db.session.commit()
