import click
from flask.cli import with_appcontext
from app.model.role import Role


@click.command("seed")
@with_appcontext
def seed_db():
    """Seed the database with default roles."""
    if Role.check_default_roles_exist():
        click.echo("Default roles already exist.")
        return

    Role.create_default_roles()
    click.echo("Successfully created default roles.")
