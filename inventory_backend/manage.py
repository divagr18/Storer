"""Django's command-line utility for administrative tasks."""

import os
import sys


def main():
    """Entry point for running Django administrative tasks for the inventory_backend project.

    This function sets the default Django settings module, imports the Django management utility,
    and executes the command line arguments passed to the script. It ensures that Django is
    installed and available in the environment, raising an ImportError with a helpful message
    if not.

    Args:
        None

    Returns:
        None

    Raises:
        ImportError: If Django is not installed or not found in the PYTHONPATH."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory_backend.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available on your PYTHONPATH environment variable? Did you forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
