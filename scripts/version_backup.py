#!/usr/bin/env python3
"""OWNEX OMEGA Version Backup CLI.

Provides command-line interface for version backup and rollback operations.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cores.version_backup import get_version_backup_system


def main():
    parser = argparse.ArgumentParser(description="OWNEX OMEGA Version Backup CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a version backup")
    backup_parser.add_argument("--notes", "-n", default="", help="Backup notes")

    # List command
    subparsers.add_parser("list", help="List all backups")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify backup integrity")
    verify_parser.add_argument("backup_path", help="Path to backup directory")

    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Rollback to a specific version")
    rollback_parser.add_argument("--version", "-v", help="Version to rollback to")
    rollback_parser.add_argument("--commit", "-c", help="Git commit to rollback to")

    # Restore latest command
    subparsers.add_parser("restore-latest", help="Restore from the latest backup")

    # Current version command
    subparsers.add_parser("current", help="Get current version information")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    backup_system = get_version_backup_system()

    if args.command == "backup":
        print(f"[OWNEX BACKUP] Creating backup: {args.notes}")
        result = backup_system.create_backup(notes=args.notes)

        if result.status.value == "success":
            print(f"[OWNEX BACKUP] Backup created successfully!")
            print(f"  Version: {result.version}")
            print(f"  Path: {result.backup_path}")
            print(f"  Size: {result.manifest.get('size', 0) / 1024 / 1024:.2f} MB")
        else:
            print(f"[OWNEX BACKUP] Backup failed: {result.error}")
            sys.exit(1)

    elif args.command == "list":
        backups = backup_system.list_backups()

        if not backups:
            print("[OWNEX BACKUP] No backups available")
            return

        print(f"[OWNEX BACKUP] {len(backups)} backups available:")
        for backup in backups:
            print(f"  Version: {backup['version']}")
            print(f"    Commit: {backup['git_commit']}")
            print(f"    Created: {backup['created_at']}")
            print(f"    State: {backup['state']}")
            print(f"    Size: {backup['size'] / 1024 / 1024:.2f} MB")
            print(f"    Notes: {backup['notes']}")
            print()

    elif args.command == "verify":
        print(f"[OWNEX BACKUP] Verifying backup: {args.backup_path}")
        verification = backup_system.verify_backup(args.backup_path)

        if verification["valid"]:
            print("[OWNEX BACKUP] Backup is valid!")
            print(f"  Version: {verification['version']}")
            print(f"  Commit: {verification['git_commit']}")
            print(f"  Created: {verification['created_at']}")
            print(f"  Size: {verification['size'] / 1024 / 1024:.2f} MB")
        else:
            print(f"[OWNEX BACKUP] Backup verification failed: {verification['error']}")
            sys.exit(1)

    elif args.command == "rollback":
        print(f"[OWNEX BACKUP] Rolling back to version: {args.version or args.commit}")
        result = backup_system.rollback_to_version(
            version=args.version,
            git_commit=args.commit,
        )

        if result["success"]:
            print("[OWNEX BACKUP] Rollback completed successfully!")
            print(f"  Version: {result['version']}")
            print(f"  Commit: {result['git_commit']}")
        else:
            print(f"[OWNEX BACKUP] Rollback failed: {result['error']}")
            sys.exit(1)

    elif args.command == "restore-latest":
        print("[OWNEX BACKUP] Restoring from latest backup")
        result = backup_system.restore_latest()

        if result["success"]:
            print("[OWNEX BACKUP] Restore completed successfully!")
            print(f"  Version: {result['version']}")
            print(f"  Commit: {result['git_commit']}")
        else:
            print(f"[OWNEX BACKUP] Restore failed: {result['error']}")
            sys.exit(1)

    elif args.command == "current":
        version = backup_system.get_current_version()
        commit = backup_system.get_current_commit()

        print("[OWNEX BACKUP] Current version information:")
        print(f"  Version: {version}")
        print(f"  Commit: {commit}")


if __name__ == "__main__":
    main()
