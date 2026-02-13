"""
Admin CLI commands for user management and system maintenance.

Usage:
    python -m src.cli.admin create-admin
    python -m src.cli.admin create-user <username> <email>
    python -m src.cli.admin list-users
    python -m src.cli.admin delete-user <username>
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.db.session import get_session
from src.db.repositories.user_repository import UserRepository
from src.api.schemas.auth import UserCreate
from src.db.models import UserRole
from getpass import getpass


async def create_admin_user():
    """Create an admin user interactively."""
    print("\n=== Create Admin User ===\n")
    
    username = input("Username: ").strip()
    if not username:
        print("Error: Username is required")
        return
    
    email = input("Email: ").strip()
    if not email:
        print("Error: Email is required")
        return
    
    full_name = input("Full Name (optional): ").strip() or None
    
    password = getpass("Password: ")
    password_confirm = getpass("Confirm Password: ")
    
    if password != password_confirm:
        print("Error: Passwords do not match")
        return
    
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        return
    
    async for session in get_session():
        repo = UserRepository(session)
        
        # Check if user already exists
        existing = await repo.get_by_username(username)
        if existing:
            print(f"Error: User '{username}' already exists")
            return
        
        existing = await repo.get_by_email(email)
        if existing:
            print(f"Error: Email '{email}' already in use")
            return
        
        # Create admin user
        user_data = UserCreate(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=UserRole.ADMIN,
        )
        
        user = await repo.create(user_data)
        await session.commit()
        
        print(f"\n✅ Admin user created successfully!")
        print(f"   ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role.value}")


async def create_regular_user(username: str, email: str, role: str = "user"):
    """Create a regular user with command-line args."""
    print(f"\n=== Create {role.title()} User ===\n")
    
    full_name = input(f"Full Name for {username} (optional): ").strip() or None
    password = getpass("Password: ")
    password_confirm = getpass("Confirm Password: ")
    
    if password != password_confirm:
        print("Error: Passwords do not match")
        return
    
    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        return
    
    # Validate role
    try:
        user_role = UserRole(role)
    except ValueError:
        print(f"Error: Invalid role '{role}'. Valid roles: admin, user, viewer")
        return
    
    async for session in get_session():
        repo = UserRepository(session)
        
        # Check if user already exists
        existing = await repo.get_by_username(username)
        if existing:
            print(f"Error: User '{username}' already exists")
            return
        
        existing = await repo.get_by_email(email)
        if existing:
            print(f"Error: Email '{email}' already in use")
            return
        
        # Create user
        user_data = UserCreate(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=user_role,
        )
        
        user = await repo.create(user_data)
        await session.commit()
        
        print(f"\n✅ User created successfully!")
        print(f"   ID: {user.id}")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role.value}")


async def list_users():
    """List all users in the system."""
    async for session in get_session():
        repo = UserRepository(session)
        users = await repo.list_users()
        
        if not users:
            print("\nNo users found")
            return
        
        print(f"\n=== Users ({len(users)}) ===\n")
        print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Role':<10} {'Active':<8} {'Verified':<10}")
        print("-" * 95)
        
        for user in users:
            active = "✅" if user.is_active else "❌"
            verified = "✅" if user.is_verified else "❌"
            print(f"{user.id:<5} {user.username:<20} {user.email:<30} {user.role.value:<10} {active:<8} {verified:<10}")


async def delete_user(username: str):
    """Delete a user by username."""
    print(f"\n=== Delete User: {username} ===\n")
    
    confirm = input(f"Are you sure you want to delete user '{username}'? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled")
        return
    
    async for session in get_session():
        repo = UserRepository(session)
        
        user = await repo.get_by_username(username)
        if not user:
            print(f"Error: User '{username}' not found")
            return
        
        await repo.delete(user.id)
        await session.commit()
        
        print(f"✅ User '{username}' deleted successfully")


async def reset_password(username: str):
    """Reset a user's password."""
    print(f"\n=== Reset Password: {username} ===\n")
    
    new_password = getpass("New Password: ")
    confirm_password = getpass("Confirm Password: ")
    
    if new_password != confirm_password:
        print("Error: Passwords do not match")
        return
    
    if len(new_password) < 8:
        print("Error: Password must be at least 8 characters")
        return
    
    async for session in get_session():
        repo = UserRepository(session)
        
        user = await repo.get_by_username(username)
        if not user:
            print(f"Error: User '{username}' not found")
            return
        
        from src.api.auth import get_password_hash
        user.hashed_password = get_password_hash(new_password)
        await session.commit()
        
        print(f"✅ Password reset for user '{username}'")


async def promote_to_admin(username: str):
    """Promote a user to admin role."""
    print(f"\n=== Promote to Admin: {username} ===\n")
    
    confirm = input(f"Promote '{username}' to admin? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled")
        return
    
    async for session in get_session():
        repo = UserRepository(session)
        
        user = await repo.get_by_username(username)
        if not user:
            print(f"Error: User '{username}' not found")
            return
        
        if user.role == UserRole.ADMIN:
            print(f"User '{username}' is already an admin")
            return
        
        user.role = UserRole.ADMIN
        await session.commit()
        
        print(f"✅ User '{username}' promoted to admin")


def print_usage():
    """Print usage information."""
    print("""
AutoBug Admin CLI

Usage:
    python -m src.cli.admin <command> [args]

Commands:
    create-admin                    Create an admin user (interactive)
    create-user <username> <email>  Create a regular user
    list-users                      List all users
    delete-user <username>          Delete a user
    reset-password <username>       Reset a user's password
    promote-admin <username>        Promote user to admin
    help                            Show this help message

Examples:
    python -m src.cli.admin create-admin
    python -m src.cli.admin create-user alice alice@example.com
    python -m src.cli.admin list-users
    python -m src.cli.admin delete-user bob
    python -m src.cli.admin reset-password alice
    python -m src.cli.admin promote-admin alice
""")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "create-admin":
            await create_admin_user()
        
        elif command == "create-user":
            if len(sys.argv) < 4:
                print("Error: create-user requires <username> <email>")
                print("Usage: python -m src.cli.admin create-user alice alice@example.com")
                return
            username = sys.argv[2]
            email = sys.argv[3]
            role = sys.argv[4] if len(sys.argv) > 4 else "user"
            await create_regular_user(username, email, role)
        
        elif command == "list-users":
            await list_users()
        
        elif command == "delete-user":
            if len(sys.argv) < 3:
                print("Error: delete-user requires <username>")
                print("Usage: python -m src.cli.admin delete-user alice")
                return
            username = sys.argv[2]
            await delete_user(username)
        
        elif command == "reset-password":
            if len(sys.argv) < 3:
                print("Error: reset-password requires <username>")
                print("Usage: python -m src.cli.admin reset-password alice")
                return
            username = sys.argv[2]
            await reset_password(username)
        
        elif command == "promote-admin":
            if len(sys.argv) < 3:
                print("Error: promote-admin requires <username>")
                print("Usage: python -m src.cli.admin promote-admin alice")
                return
            username = sys.argv[2]
            await promote_to_admin(username)
        
        elif command in ["help", "-h", "--help"]:
            print_usage()
        
        else:
            print(f"Error: Unknown command '{command}'")
            print_usage()
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
