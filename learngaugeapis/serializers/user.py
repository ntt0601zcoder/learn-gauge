import re
from rest_framework import serializers
from learngaugeapis.models.user import User, UserRole, UserStatus, UserGender

class UserSerializer(serializers.ModelSerializer):
    class Meta: 
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        existing = set(self.fields.keys())
        fields = kwargs.pop("fields", []) or existing
        exclude = kwargs.pop("exclude", [])
        
        super().__init__(*args, **kwargs)
        
        for field in exclude + list(set(existing) - set(fields)):
            self.fields.pop(field, None)

class CreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    card_id = serializers.CharField(required=True)
    fullname = serializers.CharField(required=True)
    birth_date = serializers.DateField(required=True)
    gender = serializers.ChoiceField(choices=UserGender.choices, required=True)
    phone = serializers.CharField(required=False)
    password = serializers.CharField(required=True)

    def validate_phone_number(self, value):
        phone_pattern = re.compile(r"^(?:\+)?[0-9]{6,14}$")
        if not phone_pattern.match(value):
            raise serializers.ValidationError("Invalid phone number!")
        
        return value
    
    def validate_password(self, value):
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_-])[A-Za-z\d@$!%_#*?&-]{8,30}$', value):
            raise serializers.ValidationError("Invalid password!")
        
        return value

class VerifyUserSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True)

class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['card_id', 'fullname', 'birth_date', 'gender', 'email', 'phone', 'status']
        extra_kwargs = {
            'card_id': {'required': False},
            'fullname': {'required': False},
            'birth_date': {'required': False},
            'gender': {'required': False},
            'email': {'required': False},
            'phone': {'required': False},
            'status': {'required': False}
        }

    def validate_phone(self, value):
        phone_pattern = re.compile(r"^(?:\+)?[0-9]{6,14}$")
        if not phone_pattern.match(value):
            raise serializers.ValidationError("Invalid phone number!")
        return value

    def validate(self, data):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")

        user_allowed_fields = {'fullname', 'birth_date', 'gender', 'phone'}
        admin_only_fields = {'card_id', 'email', 'status'}

        attempted_fields = set(data.keys())

        if request.user.role == UserRole.ROOT:
            invalid_fields = attempted_fields - admin_only_fields
            if invalid_fields:
                raise serializers.ValidationError(
                    f"Admin only allowed to update fields: {', '.join(admin_only_fields)}"
                )
        else:
            if request.user.id != self.instance.id:
                raise serializers.ValidationError("You can only update your own information")

            invalid_fields = attempted_fields - user_allowed_fields
            if invalid_fields:
                raise serializers.ValidationError(
                    f"You are only allowed to update fields: {', '.join(user_allowed_fields)}"
                )

        if 'status' in data and request.user.id == self.instance.id:
            raise serializers.ValidationError("Cannot change your own status")

        return data

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context.get('user')
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect!")
        return value

    def validate_new_password(self, value):
        if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&_-])[A-Za-z\d@$!%_#*?&-]{8,30}$', value):
            raise serializers.ValidationError("Invalid password!")
        
        return value 