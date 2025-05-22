from middleware.main_middleware import origins


def validate_uri(redirect_uri: str) -> str:
    if not (redirect_uri and redirect_uri.startswith(tuple(origins))):
        raise ValueError("Invalid redirect URI")
    return redirect_uri