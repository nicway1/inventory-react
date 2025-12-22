"""
Mac Model Identifier to Human-Readable Name Mapping

This module provides translation from Mac model identifiers (e.g., Mac14,7)
to human-readable product names (e.g., MacBook Pro 13" M2 2022).

Sources:
- https://everymac.com/systems/by_capability/mac-specs-by-machine-model-machine-id.html
- https://appledb.dev/device-selection/Macs.html
- https://support.apple.com/en-us/108052
"""

MAC_MODEL_MAP = {
    # M4 Macs (2024-2025)
    "Mac16,1": "MacBook Pro 14\" M4 (2024)",
    "Mac16,2": "iMac 24\" M4 (2024)",
    "Mac16,3": "iMac 24\" M4 (2024)",
    "Mac16,5": "MacBook Pro 16\" M4 Max (2024)",
    "Mac16,6": "MacBook Pro 14\" M4 Pro (2024)",
    "Mac16,7": "MacBook Pro 16\" M4 Pro (2024)",
    "Mac16,8": "MacBook Pro 14\" M4 Pro/Max (2024)",
    "Mac16,10": "Mac mini M4 (2024)",
    "Mac16,11": "Mac mini M4 Pro (2024)",
    "Mac16,12": "MacBook Air 13\" M4 (2025)",
    "Mac16,13": "MacBook Air 15\" M4 (2025)",

    # M3 Macs (2023-2024)
    "Mac15,3": "MacBook Pro 14\" M3 (2023)",
    "Mac15,4": "iMac 24\" M3 (2023)",
    "Mac15,5": "iMac 24\" M3 (2023)",
    "Mac15,6": "MacBook Pro 14\" M3 Pro (2023)",
    "Mac15,7": "MacBook Pro 16\" M3 Pro (2023)",
    "Mac15,8": "MacBook Pro 14\" M3 Max (2023)",
    "Mac15,9": "MacBook Pro 16\" M3 Max (2023)",
    "Mac15,10": "MacBook Pro 14\" M3 Pro/Max (2023)",
    "Mac15,11": "MacBook Pro 16\" M3 Pro/Max (2023)",
    "Mac15,12": "MacBook Air 13\" M3 (2024)",
    "Mac15,13": "MacBook Air 15\" M3 (2024)",

    # M2 Macs (2022-2023)
    "Mac14,2": "MacBook Air 13\" M2 (2022)",
    "Mac14,3": "Mac mini M2 (2023)",
    "Mac14,5": "MacBook Pro 14\" M2 Max (2023)",
    "Mac14,6": "MacBook Pro 16\" M2 Max (2023)",
    "Mac14,7": "MacBook Pro 13\" M2 (2022)",
    "Mac14,9": "MacBook Pro 14\" M2 Pro (2023)",
    "Mac14,10": "MacBook Pro 16\" M2 Pro (2023)",
    "Mac14,12": "Mac mini M2 Pro (2023)",
    "Mac14,13": "Mac Studio M2 Max (2023)",
    "Mac14,14": "Mac Studio M2 Ultra (2023)",
    "Mac14,15": "MacBook Air 15\" M2 (2023)",

    # M1 Macs (2020-2022)
    "Mac13,1": "Mac Studio M1 Max (2022)",
    "Mac13,2": "Mac Studio M1 Ultra (2022)",
    "MacBookAir10,1": "MacBook Air 13\" M1 (2020)",
    "MacBookPro17,1": "MacBook Pro 13\" M1 (2020)",
    "MacBookPro18,1": "MacBook Pro 16\" M1 Pro (2021)",
    "MacBookPro18,2": "MacBook Pro 16\" M1 Max (2021)",
    "MacBookPro18,3": "MacBook Pro 14\" M1 Pro (2021)",
    "MacBookPro18,4": "MacBook Pro 14\" M1 Max (2021)",
    "Macmini9,1": "Mac mini M1 (2020)",
    "iMac21,1": "iMac 24\" M1 (2021)",
    "iMac21,2": "iMac 24\" M1 (2021)",

    # Intel MacBook Pro (2015-2020)
    "MacBookPro11,4": "MacBook Pro 15\" Mid 2015",
    "MacBookPro11,5": "MacBook Pro 15\" Mid 2015 (DG)",
    "MacBookPro12,1": "MacBook Pro 13\" Early 2015",
    "MacBookPro13,1": "MacBook Pro 13\" Late 2016",
    "MacBookPro13,2": "MacBook Pro 13\" Late 2016 (Touch Bar)",
    "MacBookPro13,3": "MacBook Pro 15\" Late 2016 (Touch Bar)",
    "MacBookPro14,1": "MacBook Pro 13\" Mid 2017",
    "MacBookPro14,2": "MacBook Pro 13\" Mid 2017 (Touch Bar)",
    "MacBookPro14,3": "MacBook Pro 15\" Mid 2017 (Touch Bar)",
    "MacBookPro15,1": "MacBook Pro 15\" 2018 (Touch Bar)",
    "MacBookPro15,2": "MacBook Pro 13\" 2018 (Touch Bar)",
    "MacBookPro15,3": "MacBook Pro 15\" 2019 (Touch Bar)",
    "MacBookPro15,4": "MacBook Pro 13\" 2019 (Touch Bar)",
    "MacBookPro16,1": "MacBook Pro 16\" 2019",
    "MacBookPro16,2": "MacBook Pro 13\" 2020 (4 TB3)",
    "MacBookPro16,3": "MacBook Pro 13\" 2020 (2 TB3)",
    "MacBookPro16,4": "MacBook Pro 16\" 2019 (AMD)",

    # Intel MacBook Air (2015-2020)
    "MacBookAir7,1": "MacBook Air 11\" Early 2015",
    "MacBookAir7,2": "MacBook Air 13\" Early 2015",
    "MacBookAir8,1": "MacBook Air 13\" Late 2018",
    "MacBookAir8,2": "MacBook Air 13\" 2019",
    "MacBookAir9,1": "MacBook Air 13\" 2020",

    # Intel MacBook (2015-2017)
    "MacBook8,1": "MacBook 12\" Early 2015",
    "MacBook9,1": "MacBook 12\" Early 2016",
    "MacBook10,1": "MacBook 12\" Mid 2017",

    # Intel Mac mini (2014-2018)
    "Macmini7,1": "Mac mini Late 2014",
    "Macmini8,1": "Mac mini Late 2018",

    # Intel iMac (2015-2020)
    "iMac15,1": "iMac 27\" 5K Late 2014",
    "iMac16,1": "iMac 21.5\" Late 2015",
    "iMac16,2": "iMac 21.5\" 4K Late 2015",
    "iMac17,1": "iMac 27\" 5K Late 2015",
    "iMac18,1": "iMac 21.5\" Mid 2017",
    "iMac18,2": "iMac 21.5\" 4K Mid 2017",
    "iMac18,3": "iMac 27\" 5K Mid 2017",
    "iMac19,1": "iMac 27\" 5K 2019",
    "iMac19,2": "iMac 21.5\" 4K 2019",
    "iMac20,1": "iMac 27\" 5K 2020",
    "iMac20,2": "iMac 27\" 5K 2020",
    "iMacPro1,1": "iMac Pro 27\" 2017",

    # Intel Mac Pro
    "MacPro6,1": "Mac Pro Late 2013",
    "MacPro7,1": "Mac Pro 2019",
}


def get_mac_model_name(model_id: str) -> str:
    """
    Translate a Mac model identifier to a human-readable name.

    Args:
        model_id: The Mac model identifier (e.g., "Mac14,7", "MacBookPro18,3")

    Returns:
        Human-readable name if found, otherwise returns the original model_id
    """
    if not model_id:
        return "Unknown"

    # Clean up the model_id
    model_id = model_id.strip()

    # Direct lookup
    if model_id in MAC_MODEL_MAP:
        return MAC_MODEL_MAP[model_id]

    # Try without any extra whitespace or characters
    clean_id = ''.join(model_id.split())
    if clean_id in MAC_MODEL_MAP:
        return MAC_MODEL_MAP[clean_id]

    # Return original if not found
    return model_id


def get_all_models() -> dict:
    """Return the complete model mapping dictionary."""
    return MAC_MODEL_MAP.copy()
