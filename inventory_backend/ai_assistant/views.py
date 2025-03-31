from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
import semantic_kernel as sk
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings
from .apps import AiAssistantConfig
import logging
from asgiref.sync import async_to_sync
from drf_spectacular.utils import extend_schema
from semantic_kernel import Kernel
logger = logging.getLogger(__name__)
import json
# In-memory store for chat histories (resets on server restart)
chat_histories = {}

@extend_schema(exclude=True)
class ChatAPIView(APIView):
    """
    API endpoint for interacting with the inventory AI assistant powered by Semantic Kernel.
    Handles user messages, manages chat history per user, invokes the kernel with
    tool usage enabled, and returns the AI's response.
    (Excluded from OpenAPI Schema)
    """
    permission_classes = [permissions.AllowAny]  # Change to IsAuthenticated if required

    def post(self, request, *args, **kwargs):
        """Handles POST requests containing the user's message."""
        kernel = AiAssistantConfig.get_kernel()
        
        if not kernel:
            logger.error("ChatAPIView: Kernel not available (check initialization logs).")
            return Response(
                {"error": "AI Assistant is currently unavailable due to configuration error."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # --- User Identification ---
        if request.user and request.user.is_authenticated:
            user_id = f"user_{request.user.id}"  # Prefix to avoid clashes
        else:
            if not request.session.session_key:
                request.session.create()
            user_id = f"session_{request.session.session_key}"
            logger.debug(f"Handling chat for anonymous session: {user_id}")

        # --- Message Handling ---
        user_message = request.data.get('message')
        if not user_message:
            return Response(
                {"error": "The 'message' field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        logger.info(f"Received chat message from '{user_id}': {user_message}")

        # Extract the product ID from the user message (assuming it's provided in a specific format)
        product_id = None
        if "-" in user_message:
            try:
                # Split the message to get the SKU part and then extract the product ID
                product_id = user_message.split("-")[1].strip()  # Extract the product ID after the hyphen
            except IndexError:
                logger.error(f"Invalid product ID format in message: {user_message}")

        if not product_id:
            return Response(
                {"error": "Product ID is required but not provided in the message."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Chat History Management ---
        if user_id not in chat_histories:
            system_prompt = (
                "You are StoReBot, an AI assistant for the Storer inventory management system.\n"
                "Your goal is to help users by answering questions and performing tasks related to inventory "
                "using the available tools (API functions). Available tools include functions like "
                "'InventoryAPI.api_products_list', 'InventoryAPI.api_products_retrieve', "
                "'InventoryAPI.api_inventory_logs_list', etc. (Refer to your tool list if unsure).\n"
                "ONLY use these tools when necessary to get information or perform actions requested by the user.\n"
                "If a tool requires specific input (like a product SKU) and the user hasn't provided it, ask for clarification.\n"
                "Be concise, helpful, and accurate. Do not invent information if the tools cannot provide it."
            )
            chat_histories[user_id] = ChatHistory(system_message=system_prompt)
            logger.info(f"Initialized new chat history for '{user_id}'.")

        history: ChatHistory = chat_histories[user_id]
        history.add_user_message(user_message)

        try:
            # Configure Kernel Invocation
            settings = OpenAIPromptExecutionSettings(
                service_id="openai_chat",
                tool_choice="auto"
            )

            function_name = "api_products_retrieve"
            plugin_name = "InventoryAPI"

            logger.debug(f"Invoking kernel function '{plugin_name}-{function_name}' for user '{user_id}' with product ID '{product_id}'.")

            # --- Kernel Invocation with Keyword Arguments ---
            # Pass the arguments as keyword arguments
            chat_result: ChatMessageContent = async_to_sync(kernel.invoke)(
                function_name=function_name,
                plugin_name=plugin_name,
                history=history,
                settings=settings,
                id=product_id  # Directly passing the product_id as a keyword argument
            )

            logger.debug(f"Kernel invocation completed for '{user_id}'. Result: {chat_result}")

            # --- Process Results ---
            if not chat_result:
                logger.warning(f"Kernel returned no valid results for '{user_id}'.")
                ai_response_text = "I'm sorry, I couldn't generate a response right now."
            else:
                # Log the available attributes of the FunctionResult to check the structure
                logger.debug(f"FunctionResult attributes: {dir(chat_result)}")

                # Check if the result is a FunctionResult
                if isinstance(chat_result, sk.functions.function_result.FunctionResult):
                    # Parse the 'value' string into a dictionary
                    try:
                        result_data = json.loads(chat_result.value)
                        
                        # Log the parsed result to inspect the structure
                        logger.debug(f"Parsed FunctionResult data: {result_data}")

                        # Extract relevant fields
                        ai_response_text = f"Product Name: {result_data.get('name')}\n" \
                                        f"Description: {result_data.get('description')}\n" \
                                        f"Stock Level: {result_data.get('stock_level')}\n" \
                                        f"Price: {result_data.get('price')}\n" \
                                        f"Category: {result_data.get('category')}"
                        logger.debug(f"Formatted response from kernel: {ai_response_text}")
                    except json.JSONDecodeError as e:
                        ai_response_text = "There was an error decoding the product data."
                        logger.error(f"Error decoding JSON for '{user_id}': {e}")
                else:
                    ai_response_text = "I'm sorry, the response format is not as expected."
                    logger.warning(f"Unexpected result format for '{user_id}': {type(chat_result)}")
            # --- Process Results ---
            
            if not ai_response_text and chat_result.tool_calls:
                ai_response_text = "Okay, I will use my tools to find that information or perform that action."
                logger.info(f"AI response for '{user_id}' consists of tool calls. Sending placeholder text.")

            # --- Optional History Trimming ---
            max_history_items = 10  # Define your limit for stored messages
            if len(history.messages) > max_history_items:
                try:
                    # Always retain the system message at index 0 if it exists
                    system_message = history.messages[0] if history.messages and history.messages[0].role == "system" else None
                    latest_messages = history.messages[-max_history_items:]
                    if system_message and system_message not in latest_messages:
                        chat_histories[user_id]._messages = [system_message] + latest_messages
                    else:
                        chat_histories[user_id]._messages = latest_messages
                    logger.debug(f"Chat history for '{user_id}' trimmed to the last {max_history_items} messages.")
                except Exception as trim_err:
                    logger.warning(f"Could not trim history for '{user_id}': {trim_err}")

            logger.info(f"Sending AI response to '{user_id}': '{ai_response_text}'")
            return Response({"response": ai_response_text}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error during Semantic Kernel operation for '{user_id}': {e}")
            return Response(
                {"error": "An internal error occurred while processing your request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

