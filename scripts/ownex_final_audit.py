"""OWNEX FINAL AUDIT — Complete Excellence Audit

Comprehensive audit of OWNEX according to the Final Excellence Protocol.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path("/home/adrie/projects/Rastro")


def check_backend() -> dict:
    """Audit backend state."""
    print("\n=== BACKEND AUDIT ===")

    # Check FastAPI main
    main_py = PROJECT_ROOT / "api" / "main.py"
    if main_py.exists():
        print("✓ FastAPI main.py exists")
    else:
        print("❌ FastAPI main.py missing")

    # Check database
    db_files = list(PROJECT_ROOT.glob("*.db"))
    print(f"✓ Database files: {len(db_files)}")
    for db in db_files:
        print(f"  - {db.name}")

    # Check routers
    routers_dir = PROJECT_ROOT / "api" / "routers"
    routers = list(routers_dir.glob("*.py"))
    print(f"✓ API Routers: {len(routers)}")

    # Check tests
    tests_dir = PROJECT_ROOT / "tests"
    test_files = list(tests_dir.glob("test_*.py"))
    print(f"✓ Test files: {len(test_files)}")

    return {"main_py": main_py.exists(), "routers": len(routers), "tests": len(test_files)}


def check_frontend() -> dict:
    """Audit frontend state."""
    print("\n=== FRONTEND AUDIT ===")

    # Check Vue project
    frontend_dir = PROJECT_ROOT / "frontend"
    package_json = frontend_dir / "package.json"
    if package_json.exists():
        print("✓ Frontend package.json exists")
        with open(package_json) as f:
            pkg = json.load(f)
            print(f"  - Vue: {pkg.get('dependencies', {}).get('vue', 'N/A')}")
            print(f"  - TypeScript: {pkg.get('devDependencies', {}).get('typescript', 'N/A')}")
    else:
        print("❌ Frontend package.json missing")

    # Check pages
    pages_dir = frontend_dir / "src" / "pages"
    pages = list(pages_dir.glob("*.vue"))
    print(f"✓ Frontend pages: {len(pages)}")

    # Check components
    components_dir = frontend_dir / "src" / "components"
    components = list(components_dir.rglob("*.vue"))
    print(f"✓ Frontend components: {len(components)}")

    return {"package_json": package_json.exists(), "pages": len(pages), "components": len(components)}


def check_desktop() -> dict:
    """Audit desktop state."""
    print("\n=== DESKTOP AUDIT ===")

    # Check Tauri
    tauri_dir = PROJECT_ROOT / "src-tauri"
    if tauri_dir.exists():
        print("✓ Tauri directory exists")
        cargo_toml = tauri_dir / "Cargo.toml"
        if cargo_toml.exists():
            print("✓ Cargo.toml exists")
        else:
            print("❌ Cargo.toml missing")
    else:
        print("❌ Tauri directory missing")

    # Check PyInstaller dist
    dist_dir = PROJECT_ROOT / "dist"
    if dist_dir.exists():
        print("✓ Dist directory exists")
        executables = list(dist_dir.glob("*"))
        print(f"  - Executables: {len(executables)}")
    else:
        print("❌ Dist directory missing")

    return {"tauri": tauri_dir.exists(), "dist": dist_dir.exists()}


def check_mobile() -> dict:
    """Audit mobile state."""
    print("\n=== MOBILE AUDIT ===")

    # Check Android
    android_dir = PROJECT_ROOT / "android"
    if android_dir.exists():
        print("✓ Android directory exists")
        build_gradle = android_dir / "app" / "build.gradle"
        if build_gradle.exists():
            print("✓ build.gradle exists")
        else:
            print("❌ build.gradle missing")
    else:
        print("❌ Android directory missing")

    # Check WearOS
    wearos_dir = PROJECT_ROOT / "wearos"
    if wearos_dir.exists():
        print("✓ WearOS directory exists")
        wearos_files = list(wearos_dir.rglob("*"))
        print(f"  - Files: {len(wearos_files)}")
    else:
        print("❌ WearOS directory missing")

    return {"android": android_dir.exists(), "wearos": wearos_dir.exists()}


def check_ai() -> dict:
    """Audit AI systems."""
    print("\n=== AI AUDIT ===")

    # Check AI providers
    ai_dir = PROJECT_ROOT / "core" / "ai"
    if ai_dir.exists():
        print("✓ Core AI directory exists")
        ai_files = list(ai_dir.glob("*.py"))
        print(f"  - AI files: {len(ai_files)}")
    else:
        print("❌ Core AI directory missing")

    # Check agents
    agents_dir = PROJECT_ROOT / "cores" / "agents"
    if agents_dir.exists():
        print("✓ Agents directory exists")
        agent_files = list(agents_dir.rglob("*.py"))
        print(f"  - Agent files: {len(agent_files)}")
    else:
        print("❌ Agents directory missing")

    return {"ai": ai_dir.exists(), "agents": agents_dir.exists()}


def check_documentation() -> dict:
    """Audit documentation."""
    print("\n=== DOCUMENTATION AUDIT ===")

    # Check README
    readme = PROJECT_ROOT / "README.md"
    if readme.exists():
        print("✓ README.md exists")
        with open(readme) as f:
            lines = len(f.readlines())
            print(f"  - Lines: {lines}")
    else:
        print("❌ README.md missing")

    # Check .ai docs
    ai_dir = PROJECT_ROOT / ".ai"
    if ai_dir.exists():
        print("✓ .ai directory exists")
        ai_files = list(ai_dir.glob("*.md"))
        print(f"  - .ai docs: {len(ai_files)}")
    else:
        print("❌ .ai directory missing")

    return {"readme": readme.exists(), "ai_docs": len(ai_files) if ai_dir.exists() else 0}


def main():
    """Run complete audit."""
    print("OWNEX FINAL AUDIT — Complete Excellence Audit")
    print("=" * 60)

    audit_results = {
        "backend": check_backend(),
        "frontend": check_frontend(),
        "desktop": check_desktop(),
        "mobile": check_mobile(),
        "ai": check_ai(),
        "documentation": check_documentation(),
    }

    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)

    # Calculate completion percentage
    total_checks = 6
    passed_checks = sum(
        1
        for result in audit_results.values()
        if isinstance(result, dict)
        and result.get("package_json")
        or result.get("main_py")
        or result.get("tauri")
        or result.get("android")
        or result.get("ai")
        or result.get("readme")
    )

    print(f"Basic Infrastructure: {passed_checks}/{total_checks} components exist")

    # Save audit results
    audit_file = PROJECT_ROOT / "OWNEX_FINAL_AUDIT.md"
    with open(audit_file, "w") as f:
        f.write("# OWNEX FINAL AUDIT\n\n")
        f.write("## Audit Results\n\n")
        f.write("### Backend\n")
        f.write(f"- Main.py: {'✓' if audit_results['backend']['main_py'] else '❌'}\n")
        f.write(f"- Routers: {audit_results['backend']['routers']}\n")
        f.write(f"- Tests: {audit_results['backend']['tests']}\n")
        f.write("\n### Frontend\n")
        f.write(f"- Package.json: {'✓' if audit_results['frontend']['package_json'] else '❌'}\n")
        f.write(f"- Pages: {audit_results['frontend']['pages']}\n")
        f.write(f"- Components: {audit_results['frontend']['components']}\n")
        f.write("\n### Desktop\n")
        f.write(f"- Tauri: {'✓' if audit_results['desktop']['tauri'] else '❌'}\n")
        f.write(f"- Dist: {'✓' if audit_results['desktop']['dist'] else '❌'}\n")
        f.write("\n### Mobile\n")
        f.write(f"- Android: {'✓' if audit_results['mobile']['android'] else '❌'}\n")
        f.write(f"- WearOS: {'✓' if audit_results['mobile']['wearos'] else '❌'}\n")
        f.write("\n### AI\n")
        f.write(f"- Core AI: {'✓' if audit_results['ai']['ai'] else '❌'}\n")
        f.write(f"- Agents: {'✓' if audit_results['ai']['agents'] else '❌'}\n")
        f.write("\n### Documentation\n")
        f.write(f"- README: {'✓' if audit_results['documentation']['readme'] else '❌'}\n")
        f.write(f"- .ai docs: {audit_results['documentation']['ai_docs']}\n")

    print(f"\n✓ Audit saved to: {audit_file}")


if __name__ == "__main__":
    main()
