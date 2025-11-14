import uuid
import ulid

# Used for getting ULID
def get_ulid():
    return str(ulid.new())

# Used for getting UUID
def get_uuid():
    return str(uuid.uuid4())