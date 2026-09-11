from rest_framework_simplejwt.tokens import RefreshToken


def build_tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["email"] = user.email
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def user_payload(user):
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_verified": user.is_verified,
    }
