"""
Migration: Sync @Mention Visibility permissions to User Visibility permissions

This migration mirrors existing @Mention user permissions to User Visibility permissions
for all COUNTRY_ADMIN and SUPERVISOR users who have mention_filter_enabled=True.

Run this script once after deployment to sync existing permissions.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.user import User, UserType
from models.user_mention_permission import UserMentionPermission
from models.user_visibility_permission import UserVisibilityPermission


def sync_mention_to_visibility():
    """Sync @Mention user permissions to User Visibility permissions for all users"""
    db_session = SessionLocal()

    try:
        # Get all COUNTRY_ADMIN and SUPERVISOR users with mention filtering enabled
        users = db_session.query(User).filter(
            User.user_type.in_([UserType.COUNTRY_ADMIN, UserType.SUPERVISOR]),
            User.mention_filter_enabled == True
        ).all()

        print(f"Found {len(users)} users with mention filtering enabled")

        synced_count = 0
        for user in users:
            # Get existing @Mention user permissions
            mention_perms = db_session.query(UserMentionPermission).filter(
                UserMentionPermission.user_id == user.id,
                UserMentionPermission.target_type == 'user'
            ).all()

            mention_user_ids = [p.target_id for p in mention_perms]

            if not mention_user_ids:
                print(f"  User {user.username} (ID:{user.id}): No @Mention user permissions to sync")
                continue

            # Delete existing visibility permissions
            deleted = db_session.query(UserVisibilityPermission).filter_by(user_id=user.id).delete()

            # Create new visibility permissions mirrored from @Mention
            for visible_user_id in mention_user_ids:
                visibility_perm = UserVisibilityPermission(
                    user_id=user.id,
                    visible_user_id=visible_user_id
                )
                db_session.add(visibility_perm)

            print(f"  User {user.username} (ID:{user.id}): Synced {len(mention_user_ids)} visibility permissions (deleted {deleted} old)")
            synced_count += 1

        db_session.commit()
        print(f"\nMigration complete! Synced {synced_count} users")

    except Exception as e:
        db_session.rollback()
        print(f"Error during migration: {str(e)}")
        raise
    finally:
        db_session.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Syncing @Mention Visibility to User Visibility permissions")
    print("=" * 60)
    sync_mention_to_visibility()
