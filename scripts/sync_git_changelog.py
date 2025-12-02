#!/usr/bin/env python3
"""
Sync Git Commits to Dev Blog

This script parses git commits and creates dev blog entries.
It can be run manually or via git hooks.

Usage:
    python scripts/sync_git_changelog.py [--count N] [--since DATE] [--branch BRANCH]

Commit message format (Conventional Commits):
    type(scope): description

    Optional body text

Types: feat, fix, refactor, docs, style, test, chore, perf, ci, build, revert
"""

import subprocess
import re
import sys
import os
from datetime import datetime
from argparse import ArgumentParser

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.dev_blog_entry import DevBlogEntry
from models.user import User


def parse_commit_message(message):
    """Parse a conventional commit message"""
    # Pattern: type(scope): description or type: description
    pattern = r'^(\w+)(?:\(([^)]+)\))?:\s*(.+)$'

    lines = message.strip().split('\n')
    first_line = lines[0].strip()

    match = re.match(pattern, first_line)
    if match:
        commit_type = match.group(1).lower()
        scope = match.group(2)
        title = match.group(3).strip()
    else:
        # Not a conventional commit, use the whole first line as title
        commit_type = None
        scope = None
        title = first_line

    # Get description from remaining lines
    description = '\n'.join(lines[1:]).strip() if len(lines) > 1 else None

    # Filter out co-authored-by and generated lines
    if description:
        clean_lines = []
        for line in description.split('\n'):
            if not line.startswith('Co-Authored-By:') and 'Generated with' not in line:
                clean_lines.append(line)
        description = '\n'.join(clean_lines).strip()
        if not description:
            description = None

    return commit_type, scope, title, description


def get_git_commits(count=50, since=None, branch=None):
    """Get recent git commits"""
    cmd = [
        'git', 'log',
        f'-{count}',
        '--format=%H|%h|%an|%ae|%aI|%s|%b|||END|||',
        '--no-merges'
    ]

    if since:
        cmd.append(f'--since={since}')

    if branch:
        cmd.append(branch)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if result.returncode != 0:
            print(f"Git error: {result.stderr}")
            return []

        commits = []
        entries = result.stdout.split('|||END|||')

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            parts = entry.split('|', 6)
            if len(parts) < 6:
                continue

            commit_hash = parts[0]
            commit_short = parts[1]
            author_name = parts[2]
            author_email = parts[3]
            commit_date_str = parts[4]
            subject = parts[5]
            body = parts[6] if len(parts) > 6 else ''

            # Parse date
            try:
                commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
            except:
                commit_date = datetime.utcnow()

            # Full message = subject + body
            full_message = subject
            if body.strip():
                full_message += '\n' + body.strip()

            commits.append({
                'hash': commit_hash,
                'short': commit_short,
                'author_name': author_name,
                'author_email': author_email,
                'date': commit_date,
                'message': full_message
            })

        return commits

    except Exception as e:
        print(f"Error getting commits: {e}")
        return []


def get_current_branch():
    """Get the current git branch"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        return result.stdout.strip()
    except:
        return None


def sync_commits(count=50, since=None, branch=None):
    """Sync git commits to the database"""
    db = SessionLocal()
    try:
        commits = get_git_commits(count, since, branch)
        current_branch = get_current_branch()

        new_count = 0
        skipped_count = 0

        for commit in commits:
            # Check if already exists
            existing = db.query(DevBlogEntry).filter(
                DevBlogEntry.commit_hash == commit['hash']
            ).first()

            if existing:
                skipped_count += 1
                continue

            # Parse commit message
            commit_type, scope, title, description = parse_commit_message(commit['message'])

            # Try to find matching user by email
            user = db.query(User).filter(User.email == commit['author_email']).first()

            # Create entry
            entry = DevBlogEntry(
                commit_hash=commit['hash'],
                commit_short=commit['short'],
                branch=current_branch or branch,
                commit_type=commit_type,
                scope=scope,
                title=title,
                description=description,
                author_name=commit['author_name'],
                author_email=commit['author_email'],
                commit_date=commit['date'],
                user_id=user.id if user else None,
                is_visible=True,
                is_highlighted=commit_type in ['feat', 'fix']  # Auto-highlight features and fixes
            )

            db.add(entry)
            new_count += 1

        db.commit()
        print(f"Synced {new_count} new commits, skipped {skipped_count} existing")
        return new_count

    except Exception as e:
        db.rollback()
        print(f"Error syncing commits: {e}")
        raise
    finally:
        db.close()


def main():
    parser = ArgumentParser(description='Sync git commits to dev blog')
    parser.add_argument('--count', '-n', type=int, default=50,
                        help='Number of commits to sync (default: 50)')
    parser.add_argument('--since', '-s', type=str,
                        help='Sync commits since date (e.g., "2024-01-01")')
    parser.add_argument('--branch', '-b', type=str,
                        help='Branch to sync (default: current branch)')

    args = parser.parse_args()

    print(f"Syncing git commits to dev blog...")
    print(f"  Count: {args.count}")
    if args.since:
        print(f"  Since: {args.since}")
    if args.branch:
        print(f"  Branch: {args.branch}")

    sync_commits(args.count, args.since, args.branch)


if __name__ == '__main__':
    main()
