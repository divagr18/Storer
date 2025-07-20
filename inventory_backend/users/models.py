from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    ROLES = [("admin", "Admin"), ("staff", "Staff")]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES, default="staff")

    def __str__(self):
        """Return the username of the associated user.

        Provides a readable string representation for the user-related model instance by returning
        the username attribute of the linked user object.

        Returns:
            str: The username of the associated user."""
        return self.user.username

    class Meta:
        db_table = "users"
