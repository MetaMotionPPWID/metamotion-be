from app.constants.default_roles import DefaultRoles
from app.extension import db
from app.model.role import Role
from app.model.association import users_roles


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(60), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    roles = db.relationship("Role", secondary=users_roles, back_populates="users")
    tokens = db.relationship(
        "TokenWhiteList", back_populates="user", cascade="all, delete-orphan"
    )

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_user_by_username(cls, login):
        return cls.query.filter_by(login=login).first()

    @classmethod
    def create_user(cls, login, password, roles_names=None):
        if roles_names is None:
            roles_names = [DefaultRoles.USER.value]

        user = cls(login=login, password=password)
        user.assign_roles(roles_names, commit=False)
        db.session.add(user)
        db.session.commit()
        return user

    def assign_roles(self, roles_names, commit=True):
        allowed_roles = [role.value for role in DefaultRoles]
        for role_name in roles_names:
            if role_name not in allowed_roles:
                raise ValueError(f"Incorrect role: {role_name}")
            role = Role.get_role_by_name(role_name)
            if not role:
                raise ValueError(f"Role {role_name} does not exist in database.")
            if role not in self.roles:
                self.roles.append(role)
        if commit:
            db.session.commit()

    def add_role(self, role_name):
        role = Role.get_role_by_name(role_name)
        if role in DefaultRoles and role not in self.roles:
            self.roles.append(role)
            db.session.commit()
