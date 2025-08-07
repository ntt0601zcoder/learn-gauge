from learngaugeapis.models.user import User, UserStatus

def custom_user_authentication_rule(user: User) -> bool:
    return user is not None and user.status == UserStatus.ACTIVATED