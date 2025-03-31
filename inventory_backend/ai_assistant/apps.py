# ai_assistant/apps.py

from django.apps import AppConfig
from django.conf import settings
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from pathlib import Path
import os
import logging
# --- Remove async_to_sync ---

logger = logging.getLogger(__name__)

class AiAssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_assistant'

    # Store kernel instance on the AppConfig class itself
    kernel_instance = None
    # Flag to prevent re-initialization attempts
    kernel_initialized = False

    # --- Remove the _initialize_kernel_async method ---

    def ready(self):
        """
        Called when Django starts. Initialize Semantic Kernel here synchronously.
        """
        if AiAssistantConfig.kernel_initialized:
            logger.debug("Semantic Kernel initialization already attempted. Skipping.")
            return

        logger.info("AiAssistantConfig.ready() called. Initializing Semantic Kernel...")
        initialization_success = False

        try:
            # 1. Get configuration
            api_key = getattr(settings, 'OPENAI_API_KEY', os.getenv("OPENAI_API_KEY"))
            org_id = getattr(settings, 'OPENAI_ORG_ID', os.getenv("OPENAI_ORG_ID"))
            chat_model_id = getattr(settings, 'OPENAI_CHAT_MODEL', "gpt-4o")
            schema_filename = getattr(settings, 'OPENAPI_SCHEMA_FILENAME', 'schema.yaml')
            schema_path = settings.BASE_DIR / schema_filename

            if not api_key:
                logger.error("OPENAI_API_KEY not found. AI Assistant cannot initialize.")
                # No need to set kernel_instance to None, it's already None
                return # Exit ready()

            # 2. Initialize the Kernel
            kernel = sk.Kernel()

            # 3. Add Chat Completion Service (Synchronous)
            service_id = "openai_chat"
            kernel.add_service(
                OpenAIChatCompletion(
                    service_id="openai_chat",
                    ai_model_id="gpt-4o-mini",
                    api_key=api_key,
                    org_id=org_id
                ),
            )
            logger.info(f"Chat service '{service_id}' added to kernel.")

            # 4. Check for OpenAPI Specification File
            if not schema_path.exists():
                logger.error(f"OpenAPI schema file not found at: {schema_path}. Cannot load InventoryAPI plugin.")
                # Store the kernel *without* the plugin, log the error.
                AiAssistantConfig.kernel_instance = kernel
                # Consider raising ImproperlyConfigured if plugin is essential
                return # Exit ready(), kernel stored partially

            # 5. Add Plugin from OpenAPI Specification File (SYNCHRONOUSLY)
            logger.info(f"Attempting to synchronously load OpenAPI plugin from {schema_path}...")
            # --- Call directly, NO await ---
            api_plugin = kernel.add_plugin_from_openapi(
                plugin_name="InventoryAPI",
                openapi_document_path=str(schema_path),
                # execution_settings=... # Add if needed
            )
            logger.info(f"OpenAPI plugin '{api_plugin.name}' loaded successfully.")

            # 6. Store the fully configured kernel
            AiAssistantConfig.kernel_instance = kernel
            initialization_success = True

        except Exception as e:
            logger.error(f"Failed during Semantic Kernel synchronous initialization: {e}", exc_info=True)
            # Ensure kernel_instance remains None on failure
            AiAssistantConfig.kernel_instance = None

        finally:
            # Mark that initialization has been attempted
            AiAssistantConfig.kernel_initialized = True
            if initialization_success:
                logger.info("Semantic Kernel initialization completed successfully.")
            else:
                logger.error("Semantic Kernel initialization failed. Check previous logs.")

    # --- Class method to safely access the kernel remains the same ---
    @classmethod
    def get_kernel(cls) -> sk.Kernel | None:
        """Safely retrieves the initialized Kernel instance."""
        if not cls.kernel_initialized:
            logger.warning("Attempted to get kernel before AppConfig.ready() completed.")
        # Check kernel_instance directly now
        elif cls.kernel_instance is None:
             logger.warning("Attempted to get kernel, but it was not successfully initialized (is None).")
        return cls.kernel_instance