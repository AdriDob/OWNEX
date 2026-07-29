"""ORION Secrets Manager — centralized API key storage.

All secrets flow through IdentityVault (AES-256-GCM encrypted on disk).
Extensions and apps never touch raw env vars directly.
"""
