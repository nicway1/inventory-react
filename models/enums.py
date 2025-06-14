from enum import Enum as PyEnum

class UserType(str, PyEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    SUPERVISOR = "SUPERVISOR"
    COUNTRY_ADMIN = "COUNTRY_ADMIN"
    CLIENT = "CLIENT"

class Country(str, PyEnum):
    USA = "USA"
    JAPAN = "JAPAN"
    PHILIPPINES = "PHILIPPINES"
    AUSTRALIA = "AUSTRALIA"
    ISRAEL = "ISRAEL"
    INDIA = "INDIA"
    IN = "IN"  # Support for existing database records
    SG = "SG"  # Support for existing database records
    SINGAPORE = "SINGAPORE" 