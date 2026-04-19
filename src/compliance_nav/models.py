"""Data models for the Compliance Navigator."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Product:
    """User-defined product description."""

    name: str
    types: list[str]  # e.g. ["heating_device", "usb_powered_device"]
    markets: list[str]  # e.g. ["EU", "US"]
    description: str = ""
    voltage_ac: Optional[float] = None
    voltage_dc: Optional[float] = None
    power_watts: Optional[float] = None
    wireless: bool = False
    battery: bool = False
    materials: list[str] = field(default_factory=list)
    food_contact: Optional[str] = None  # "direct", "indirect", None
    intended_use: str = "consumer"  # "consumer", "industrial", "medical"
    intended_age_group: Optional[str] = None  # "children", "adults", "all"


@dataclass
class Directive:
    """An EU directive or regulation."""

    id: str  # e.g. "2014/35/EU"
    short_name: str  # e.g. "LVD"
    full_name: str
    scope: str  # human-readable scope description
    market: str  # "EU" or "US" or "global"
    url: str  # link to full text
    applicability: list[dict] = field(default_factory=list)  # conditions
    key_requirements: list[str] = field(default_factory=list)
    referenced_standards: list[str] = field(default_factory=list)
    penalties: str = ""


@dataclass
class Recall:
    """A product recall record (CPSC or equivalent)."""

    recall_id: str
    date: str
    product_name: str
    description: str
    hazard: str
    remedy: str
    units: str
    category: str  # our assigned category
    injuries: int = 0
    deaths: int = 0
    manufacturer: str = ""
    url: str = ""


@dataclass
class Standard:
    """A harmonised or referenced standard."""

    id: str  # e.g. "EN 62368-1"
    name: str
    scope: str
    directive_ids: list[str] = field(default_factory=list)
    product_types: list[str] = field(default_factory=list)


@dataclass
class ChecklistItem:
    """A single compliance action item."""

    directive_id: str
    action: str  # what to do
    category: str  # "testing", "marking", "documentation", "registration"
    priority: str  # "required", "recommended", "optional"
    estimated_cost: str = ""  # e.g. "€500–2,000"
    notes: str = ""


@dataclass
class ComplianceResult:
    """Full result from a compliance check."""

    product: Product
    applicable_directives: list[Directive] = field(default_factory=list)
    applicable_standards: list[Standard] = field(default_factory=list)
    related_recalls: list[Recall] = field(default_factory=list)
    checklist: list[ChecklistItem] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
