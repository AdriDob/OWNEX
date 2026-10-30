"""Reasoners — vulnerability-specific analysis modules."""

from __future__ import annotations

from cores.offensive.reasoners.auth_bypass import AuthBypassReasoner
from cores.offensive.reasoners.bacl import BaclMatrixReasoner, BusinessFlowReasoner
from cores.offensive.reasoners.base import BaseReasoner
from cores.offensive.reasoners.cmdi import CMDIReasoner
from cores.offensive.reasoners.cors import CORSReasoner
from cores.offensive.reasoners.csrf import CSRFReasoner
from cores.offensive.reasoners.deserialization import DeserializationReasoner
from cores.offensive.reasoners.generic import GenericReasoner
from cores.offensive.reasoners.graphql import GraphQLReasoner
from cores.offensive.reasoners.idor import IDORReasoner
from cores.offensive.reasoners.lfi import LFIReasoner
from cores.offensive.reasoners.oauth import OAuthReasoner
from cores.offensive.reasoners.open_redirect import OpenRedirectReasoner
from cores.offensive.reasoners.prompt_injection import PromptInjectionReasoner
from cores.offensive.reasoners.race_condition import RaceConditionReasoner
from cores.offensive.reasoners.sqli import SQLiReasoner
from cores.offensive.reasoners.ssrf import SSRFReasoner
from cores.offensive.reasoners.xss import XSSReasoner

__all__ = [
    "BaseReasoner",
    "IDORReasoner",
    "SSRFReasoner",
    "XSSReasoner",
    "SQLiReasoner",
    "AuthBypassReasoner",
    "PromptInjectionReasoner",
    "BaclMatrixReasoner",
    "BusinessFlowReasoner",
    "GraphQLReasoner",
    "OAuthReasoner",
    "DeserializationReasoner",
    "CMDIReasoner",
    "LFIReasoner",
    "RaceConditionReasoner",
    "CORSReasoner",
    "CSRFReasoner",
    "OpenRedirectReasoner",
    "GenericReasoner",
]
