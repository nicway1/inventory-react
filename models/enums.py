from enum import Enum as PyEnum

class UserType(str, PyEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    DEVELOPER = "DEVELOPER"
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
    TAIWAN = "TAIWAN"
    CHINA = "CHINA"
    HONG_KONG = "HONG_KONG"
    MALAYSIA = "MALAYSIA"
    THAILAND = "THAILAND"
    VIETNAM = "VIETNAM"
    SOUTH_KOREA = "SOUTH_KOREA"
    INDONESIA = "INDONESIA"
    GUYANA = "GUYANA"
    UNITED_KINGDOM = "UNITED_KINGDOM"
    UAE = "UAE"
    IN = "IN"  # Support for existing database records
    SG = "SG"  # Support for existing database records
    TW = "TW"  # Support for Taiwan
    CN = "CN"  # Support for China
    HK = "HK"  # Support for Hong Kong
    MY = "MY"  # Support for Malaysia
    TH = "TH"  # Support for Thailand
    VN = "VN"  # Support for Vietnam
    KR = "KR"  # Support for South Korea
    ID = "ID"  # Support for Indonesia
    IL = "IL"  # Support for Israel
    CA = "CA"  # Support for Canada
    CANADA = "CANADA"
    SINGAPORE = "SINGAPORE"
    UK = "UK"  # Support for United Kingdom
    GB = "GB"  # Support for United Kingdom
    AE = "AE"  # Support for UAE 