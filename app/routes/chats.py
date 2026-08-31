import os
from flask import Blueprint, request, jsonify
from app.services.auth_service import login_required

# LangChain Imports
from langchain_community.utilities import SQLDatabase
from langchain_groq import ChatGroq
# Optional official Groq client (used as a direct fallback)
try:
    from groq import Groq
except Exception:
    Groq = None
from langchain_community.agent_toolkits import create_sql_agent, SQLDatabaseToolkit
import traceback

bp = Blueprint("chat", __name__, url_prefix="/api/chat")

# 1. Initialize Database Connection 
db = SQLDatabase.from_uri(
    os.environ.get("AI_DB_URI"),
    include_tables=["matters", "invoices", "tasks", "vendors", "vendor_assignments_to_matter"] 
)

# 2. Initialize the LLM (prefer Groq, fall back to OpenAI if Groq is unavailable)
# ChatGroq uses the official 'groq' Python client under the hood
# ChatOpenAI is used as a fallback when OPENAI_API_KEY is provided
groq_model = os.environ.get("GROQ_MODEL_NAME", "groq/compound")
groq_api_key = os.environ.get("GROQ_API_KEY")
llm = None
provider = None
# Official groq client instance (optional)
groq_client = None

try:
    if groq_api_key:
        # Initialize the LangChain Groq wrapper (if available)
        llm = ChatGroq(
            model_name=groq_model,
            api_key=groq_api_key,
            temperature=0,
            max_tokens=1024
        )
        provider = "groq"
        print(f"Using Groq LLM via langchain_groq: {groq_model}")
        # Try to create an official Groq client for direct calls (fallback)
        if Groq is not None:
            try:
                groq_client = Groq(api_key=groq_api_key)
                print("Initialized official Groq client for fallback use.")
            except Exception as gerr:
                groq_client = None
                print(f"Failed to initialize official Groq client: {gerr}")
    else:
        raise RuntimeError("GROQ_API_KEY not set")

except Exception as groq_err:
    print(f"Groq LLM initialization failed: {groq_err}")
    # Try OpenAI fallback if configured
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key:
        try:
            from langchain.chat_models import ChatOpenAI
            openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            llm = ChatOpenAI(temperature=0, model_name=openai_model, openai_api_key=openai_api_key)
            provider = "openai"
            print(f"Falling back to OpenAI Chat model: {openai_model}")
        except Exception as openai_err:
            print(f"OpenAI fallback failed: {openai_err}")
            raise
    else:
        # No fallback available; re-raise to fail fast with helpful message
        raise RuntimeError(
            "No working LLM available: GROQ failed and OPENAI_API_KEY not set. "
            "Set GROQ_API_KEY and valid GROQ_MODEL_NAME, or set OPENAI_API_KEY to use OpenAI as a fallback."
        )

# 3. Initialize the Toolkit 
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

# 4. Create the Agent
agent_executor = create_sql_agent(
    llm=llm,
    toolkit=toolkit, 
    verbose=True, 
    agent_type="tool-calling", 
    top_k=20,
    max_iterations=5,          # Stops infinite loops
    max_execution_time=30      # Kills the process if it hangs over 30 seconds
)

PREFIX_PROMPT = """
You are a highly capable Legal Operations AI Assistant integrated into a legal management portal.
Your job is to answer user questions by writing and executing SQL queries against the database.

Rules:
1. ONLY answer questions related to the database schema provided. 
2. If the user asks something completely unrelated to the legal portal, politely decline.
3. If a query returns no results, say "I couldn't find any records matching that criteria."
4. Format currency appropriately (e.g., $200,000 or £5,000).
5. Never expose raw SQL queries to the user. Translate the findings into a polite, conversational sentence.
"""


def _summarize_history_message(message):
    if not isinstance(message, str):
        return ""

    text = message.strip()
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    table_lines = [line for line in lines if "|" in line]
    if len(table_lines) >= 3:
        header = [part.strip() for part in table_lines[0].split("|") if part.strip()]
        columns = [part for part in header[:6] if part]
        if columns:
            return f"Displayed a table with columns: {', '.join(columns)}."
        return "Displayed a table of results."

    return text[:180].rstrip() + ("..." if len(text) > 180 else "")


def _build_context_prompt(user_message, history=None):
    history = history or []
    cleaned_history = []

    for item in history[-4:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip().lower()
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue

        cleaned_content = content.strip()
        if not cleaned_content:
            continue

        if role == "assistant":
            cleaned_content = _summarize_history_message(cleaned_content)
        else:
            cleaned_content = cleaned_content[:180].rstrip() + ("..." if len(cleaned_content) > 180 else "")

        if cleaned_content:
            cleaned_history.append({"role": role, "content": cleaned_content})

    previous_context = ""
    if cleaned_history:
        previous_lines = []
        for entry in cleaned_history:
            label = "User" if entry["role"] == "user" else "Assistant"
            previous_lines.append(f"{label}: {entry['content']}")
        previous_context = "\n\nPrevious conversation:\n" + "\n".join(previous_lines) + "\n"

    return f"{PREFIX_PROMPT}{previous_context}\nUser Question: {user_message}"


@bp.route("/", methods=["POST"])
@login_required
def process_message():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data["message"].strip()
    conversation_history = data.get("history", [])

    # Use a local executor variable so fallback recreations don't cause UnboundLocalError
    executor = agent_executor

    try:
        full_prompt = _build_context_prompt(user_message, conversation_history)

        # First attempt with the existing executor
        try:
            result = executor.invoke({"input": full_prompt})
        except Exception as invoke_err:
            invoke_err_str = str(invoke_err)
            print(f"LLM invocation error: {invoke_err_str}")
            traceback.print_exc()
            # Try groq client fallback on any invocation error
            print("Attempting groq client fallback due to invocation error...")
            if groq_client is not None:
                try:
                    messages = [{"role": "system", "content": PREFIX_PROMPT}]
                    for entry in conversation_history[-8:]:
                        if isinstance(entry, dict):
                            role = str(entry.get("role", "")).strip().lower()
                            content = entry.get("content")
                            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                                messages.append({"role": role, "content": content.strip()})
                    messages.append({"role": "user", "content": user_message})
                    # Use streaming to stay close to your playground example
                    stream_iter = groq_client.chat.completions.create(
                        model=groq_model,
                        messages=messages,
                        temperature=0,
                        max_completion_tokens=1024,
                        top_p=1,
                        stream=True,
                    )
                    collected = []
                    for chunk in stream_iter:
                        try:
                            # The official client may include partial content in choices[0].delta.content
                            delta = chunk.choices[0].delta
                            if isinstance(delta, dict):
                                collected.append(delta.get("content") or "")
                            else:
                                collected.append(str(getattr(chunk.choices[0], 'delta', '') or ''))
                        except Exception:
                            try:
                                collected.append(chunk.choices[0].text or '')
                            except Exception:
                                pass
                    groq_response = ''.join(collected).strip()
                    if groq_response:
                        print("Returning response from groq client fallback.")
                        return jsonify({"response": groq_response}), 200
                except Exception as groq_fallback_err:
                    print(f"groq client fallback failed: {groq_fallback_err}")
                    traceback.print_exc()

            print("groq client fallback not available or failed; checking OpenAI fallback...")
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if openai_api_key:
                try:
                    from langchain.chat_models import ChatOpenAI
                    openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
                    llm = ChatOpenAI(temperature=0, model_name=openai_model, openai_api_key=openai_api_key)
                    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
                    # Recreate the agent with the OpenAI LLM
                    executor = create_sql_agent(
                        llm=llm,
                        toolkit=toolkit,
                        verbose=True,
                        agent_type="tool-calling",
                        top_k=20,
                        max_iterations=5,
                        max_execution_time=30,
                    )
                    print(f"Retrying invoke with OpenAI model: {openai_model}")
                    result = executor.invoke({"input": full_prompt})
                except Exception as fallback_err:
                    print(f"OpenAI fallback invocation failed: {fallback_err}")
                    traceback.print_exc()
                    raise
            else:
                # No fallback configured; re-raise to be handled below
                raise

        bot_response = result.get("output", "I encountered an error processing your request.")

        return jsonify({"response": bot_response}), 200

    except Exception as e:
        err_str = str(e)
        print(f"Chatbot Error: {err_str}")
        traceback.print_exc()
        # Provide more actionable error for model access failures
        if ('model_not_found' in err_str) or ('does not exist' in err_str) or ("model" in err_str and "not" in err_str):
            msg = (
                "Chatbot backend error: model not found or inaccessible. "
                "Check GROQ_MODEL_NAME and GROQ_API_KEY environment variables. "
                "Set GROQ_MODEL_NAME to a valid Groq model name or configure OPENAI_API_KEY to use OpenAI as a fallback."
            )
            return jsonify({"response": "I'm sorry — the chat service is not configured with a valid model. " + msg}), 500

        return jsonify({"response": "I'm sorry, I'm having trouble retrieving that information right now."}), 500
