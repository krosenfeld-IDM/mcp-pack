import uuid

def string_to_uuid(s: str) -> str:
    # uuid.NAMESPACE_DNS is a built-in constant namespace
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))