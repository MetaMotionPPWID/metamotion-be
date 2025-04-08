from flask import Blueprint
from flask_jwt_extended import jwt_required
from permissions import user_permission
from utils.handle_errors import handle_db_errors, handle_validation_errors

sensors_bp = Blueprint('sensors', __name__)


@sensors_bp.route('/add', methods=['POST'])
@jwt_required()
@user_permission.require(http_exception=403)
@handle_validation_errors
@handle_db_errors
def register():
    return '', 201
