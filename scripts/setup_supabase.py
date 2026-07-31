#!/usr/bin/env python3
"""
Supabase Project Setup Script — Automatización de Configuración

Este script guía la creación automática de un proyecto Supabase para OWNEX OMEGA.
"""

import os
import sys
from pathlib import Path


def print_header(title: str):
    """Imprimir header formateado."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_step(step: int, total: int, message: str):
    """Imprimir paso de proceso."""
    print(f"[{step}/{total}] {message}")


def check_env_file():
    """Verificar si .env existe."""
    env_path = Path(".env")

    if not env_path.exists():
        print("❌ .env file not found")
        print("Run: cp .env.example .env")
        return False

    return True


def check_supabase_credentials():
    """Verificar credenciales de Supabase."""
    from dotenv import load_dotenv

    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not configured in .env")
        print("Please set:")
        print("  SUPABASE_URL=your_project_url")
        print("  SUPABASE_KEY=your_anon_key")
        return False

    print(f"✅ Supabase URL: {supabase_url}")
    print(f"✅ Supabase Key: {supabase_key[:20]}...")

    return True


def test_supabase_connection():
    """Probar conexión con Supabase."""
    try:
        from supabase import create_client
        from dotenv import load_dotenv

        load_dotenv()

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        client = create_client(supabase_url, supabase_key)

        # Test connection
        response = client.table('tasks').select('*').limit(1).execute()

        print("✅ Supabase connection successful")
        return True

    except ImportError:
        print("❌ Supabase client not installed")
        print("Run: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return False


def execute_schema_sql():
    """Ejecutar schema SQL en Supabase."""
    print("\n📋 To execute the schema SQL:")
    print("1. Go to your Supabase project")
    print("2. Click on SQL Editor")
    print("3. Copy the content of database/supabase_schema.sql")
    print("4. Paste in the editor and click Run")
    print("\nAlternatively, use the Supabase CLI:")
    print("  supabase db push")


def main():
    """Función principal."""
    print_header("OWNEX OMEGA — Supabase Setup Automation")

    total_steps = 4

    # Step 1: Check .env
    print_step(1, total_steps, "Checking .env file...")
    if not check_env_file():
        sys.exit(1)

    # Step 2: Check credentials
    print_step(2, total_steps, "Checking Supabase credentials...")
    if not check_supabase_credentials():
        sys.exit(1)

    # Step 3: Test connection
    print_step(3, total_steps, "Testing Supabase connection...")
    if not test_supabase_connection():
        sys.exit(1)

    # Step 4: Execute schema
    print_step(4, total_steps, "Executing schema SQL...")
    execute_schema_sql()

    print_header("Setup Complete ✅")
    print("\nNext steps:")
    print("1. Execute the schema SQL in Supabase SQL Editor")
    print("2. Test the sync endpoints: http://localhost:8000/api/supabase")
    print("3. Configure mobile apps with Supabase credentials")
    print("\nDocumentation: SUPABASE_SETUP_GUIDE.md")


if __name__ == "__main__":
    main()
