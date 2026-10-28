#!/usr/bin/env python3
"""Add a new target interactively."""

import sys

sys.path.insert(0, str(__file__).replace("/scripts/target_add.py", ""))

from database.db import SessionLocal
from database.models import Target


def main():
    if len(sys.argv) >= 3:
        name = sys.argv[1]
        domain = sys.argv[2]
    else:
        name = input("Target name: ")
        domain = input("Domain: ")

    if not name or not domain:
        print("Error: name and domain required")
        sys.exit(1)

    session = SessionLocal()
    try:
        t = Target(name=name, domain=domain, active=True)
        session.add(t)
        session.commit()
        print(f"Added Target {t.id}: {name} ({domain})")
    finally:
        session.close()


if __name__ == "__main__":
    main()
