import asyncio
import sys
import click
import logging

logger = logging.getLogger(__name__)


async def _create_admin(mobile: str, name: str, password: str) -> None:
    from app.db.session import AsyncSessionLocal
    from app.core.security import hash_password
    from app.core.constants import UserRole, UserStatus
    from app.models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.mobile_number == mobile))
        existing = result.scalar_one_or_none()
        if existing:
            click.echo(f"Error: Mobile number {mobile} is already registered.", err=True)
            sys.exit(1)

        import re
        password_regex = re.compile(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_\-#^()+={}[\]|\\:;<>,.?/~`])[A-Za-z\d@$!%*?&_\-#^()+={}[\]|\\:;<>,.?/~`]{8,}$"
        )
        if not password_regex.match(password):
            click.echo(
                "Error: Password must be at least 8 characters with uppercase, lowercase, digit, and special character.",
                err=True,
            )
            sys.exit(1)

        admin = User(
            mobile_number=mobile,
            full_name=name,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        db.add(admin)
        await db.commit()
        click.echo(f"Admin created: {name} ({mobile}) [id={admin.id}]")


@click.group()
def cli():
    pass


@cli.command("create-admin")
@click.option("--mobile", required=True, help="Admin mobile number (E.164 format)")
@click.option("--name", required=True, help="Admin full name")
@click.option("--password", required=True, prompt=True, hide_input=True, confirmation_prompt=True, help="Admin password")
def create_admin(mobile: str, name: str, password: str) -> None:
    asyncio.run(_create_admin(mobile, name, password))


if __name__ == "__main__":
    cli()
