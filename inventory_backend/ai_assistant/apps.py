from django.apps import AppConfig
from django.conf import settings
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


class AiAssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_assistant"
    kernel_instance = None
    kernel_initialized = False

    def ready(self):
        """Synchronously initialize the Semantic Kernel when Django starts.

        Checks if the kernel has already been initialized to avoid repetition. Retrieves configuration
        settings (API keys, model IDs, schema file path) from Django settings or environment variables.
        If the OpenAI API key is missing, logs an error and aborts initialization.

        Creates a new Semantic Kernel instance and adds an OpenAI chat completion service. Then attempts
        to load an OpenAPI plugin from a specified schema file, logging errors if the file is missing.

        Stores the kernel instance—either partially configured (without plugin) or fully configured—
        in the AiAssistantConfig class attribute `kernel_instance`.

        Sets the `kernel_initialized` flag to True to mark that initialization was attempted.

        Logs success or failure details throughout the process for debugging and operational visibility.

        No arguments.

        Returns:
            None"""
        if AiAssistantConfig.kernel_initialized:
            logger.debug("Semantic Kernel initialization already attempted. Skipping.")
            return
        logger.info("AiAssistantConfig.ready() called. Initializing Semantic Kernel...")
        initialization_success = False
        try:
            api_key = getattr(settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
            org_id = getattr(settings, "OPENAI_ORG_ID", os.getenv("OPENAI_ORG_ID"))
            chat_model_id = getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4o")
            schema_filename = getattr(
                settings, "OPENAPI_SCHEMA_FILENAME", "schema.yaml"
            )
            schema_path = settings.BASE_DIR / schema_filename
            if not api_key:
                logger.error(
                    "OPENAI_API_KEY not found. AI Assistant cannot initialize."
                )
                return
            kernel = sk.Kernel()
            service_id = "openai_chat"
            kernel.add_service(
                OpenAIChatCompletion(
                    service_id="openai_chat",
                    ai_model_id="gpt-4o-mini",
                    api_key=api_key,
                    org_id=org_id,
                )
            )
            logger.info(f"Chat service '{service_id}' added to kernel.")
            if not schema_path.exists():
                logger.error(
                    f"OpenAPI schema file not found at: {schema_path}. Cannot load InventoryAPI plugin."
                )
                AiAssistantConfig.kernel_instance = kernel
                return
            logger.info(
                f"Attempting to synchronously load OpenAPI plugin from {schema_path}..."
            )
            api_plugin = kernel.add_plugin_from_openapi(
                plugin_name="InventoryAPI", openapi_document_path=str(schema_path)
            )
            logger.info(f"OpenAPI plugin '{api_plugin.name}' loaded successfully.")
            AiAssistantConfig.kernel_instance = kernel
            initialization_success = True
        except Exception as e:
            logger.error(
                f"Failed during Semantic Kernel synchronous initialization: {e}",
                exc_info=True,
            )
            AiAssistantConfig.kernel_instance = None
        finally:
            AiAssistantConfig.kernel_initialized = True
            if initialization_success:
                logger.info("Semantic Kernel initialization completed successfully.")
            else:
                logger.error(
                    "Semantic Kernel initialization failed. Check previous logs."
                )

    @classmethod
    def get_kernel(cls) -> sk.Kernel | None:
        """Retrieves the initialized Kernel instance if available, otherwise returns None.

        Logs a warning if the kernel has not been initialized or if the kernel instance is None.

        Returns:
            sk.Kernel or None: The initialized Kernel object or None if it is not yet initialized or unavailable."""
        if not cls.kernel_initialized:
            logger.warning(
                "Attempted to get kernel before AppConfig.ready() completed."
            )
        elif cls.kernel_instance is None:
            logger.warning(
                "Attempted to get kernel, but it was not successfully initialized (is None)."
            )
        return cls.kernel_instance
