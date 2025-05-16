from flask_principal import Permission, RoleNeed
from app.constants.default_roles import DefaultRoles

admin_permission = Permission(RoleNeed(DefaultRoles.ADMIN.value))
user_permission = Permission(RoleNeed(DefaultRoles.USER.value))
moderator_permission = Permission(RoleNeed(DefaultRoles.MODERATOR.value))
