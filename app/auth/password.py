from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(plain_password: str) -> str:
    if not plain_password:
        raise ValueError("Password must not be empty")
    return password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str | None) -> bool:
    if not plain_password or not password_hash:
        return False
    try:
        return bool(password_hasher.verify(plain_password, password_hash))
    except Exception:
        return False