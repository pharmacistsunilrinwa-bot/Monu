import os
import asyncio
import threading
import google.generativeai as genai
from dotenv import load_dotenv

# Ensure the backend/api_keys.env is loaded dynamically regardless of where the app is launched
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
env_path = os.path.join(backend_dir, "api_keys.env")

if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
else:
    load_dotenv()

class ApiKeyManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.keys = []
        self.bad_keys = set()
        self.load_keys()

    def load_keys(self):
        """Loads keys from GEMINI_KEYS in api_keys.env or system environment."""
        gemini_keys_env = os.getenv("GEMINI_KEYS", "")
        parsed_keys = [k.strip() for k in gemini_keys_env.split(",") if k.strip()]
        
        with self._lock:
            self.keys = parsed_keys
            # Reset bad keys on a fresh load
            self.bad_keys.clear()
            
        print(f"[ApiKeyManager] Successfully loaded {len(self.keys)} API keys.")

    def get_working_keys(self) -> list:
        """Returns a list of currently working (non-skipped) API keys."""
        with self._lock:
            working = [k for k in self.keys if k not in self.bad_keys]
            if not working and self.keys:
                print("[ApiKeyManager] WARNING: All keys were marked bad. Resetting pool to try again.")
                self.bad_keys.clear()
                working = list(self.keys)
            return working

    def mark_bad_key(self, key: str):
        """Marks a key as bad/exhausted so it's skipped in subsequent calls."""
        with self._lock:
            if key in self.keys:
                self.bad_keys.add(key)
                print(f"[ApiKeyManager] Key {key[:10]}... marked as failed. Working keys remaining: {len(self.keys) - len(self.bad_keys)}/{len(self.keys)}")

def is_key_error(exception: Exception) -> bool:
    """
    Detects if the exception is due to:
    - Invalid API key / 401 Unauthorized / Unauthenticated
    - Quota limit reached / 429 Resource Exhausted / Rate limit
    - Forbidden / 403 Permission Denied (invalid scope or blocked key)
    """
    err_str = str(exception).lower()
    
    indicators = [
        "401", "unauthorized", "api_key_invalid", "api key not valid", "invalid api key", "key invalid",
        "429", "quota", "exhausted", "rate limit", "resource exhausted",
        "403", "forbidden", "permission denied"
    ]
    if any(ind in err_str for ind in indicators):
        return True
        
    try:
        from google.api_core.exceptions import PermissionDenied, ResourceExhausted, Unauthenticated, Forbidden
        if isinstance(exception, (PermissionDenied, ResourceExhausted, Unauthenticated, Forbidden)):
            return True
    except ImportError:
        pass
        
    return False

async def execute_with_failover(service_name: str, api_call_fn, model_creator_fn=None):
    """
    Executes an async Gemini operation with a robust dynamic failover mechanism.
    - service_name: Label for logging/debugging.
    - api_call_fn: Async function containing the actual Gemini call.
    - model_creator_fn: Optional synchronous callback to recreate/re-bind the model instance to the new key.
    """
    working_keys = api_key_manager.get_working_keys()
    if not working_keys:
        raise ValueError(f"[{service_name}] No API keys loaded. Please check your backend/api_keys.env configuration.")

    last_error = None
    for key in list(working_keys):
        # 1. Configure the Google GenAI SDK with the active key
        genai.configure(api_key=key)
        
        # 2. Recreate/re-bind model if a creator function was provided
        if model_creator_fn:
            model_creator_fn()
            
        try:
            # 3. Attempt the API call
            return await api_call_fn()
        except Exception as e:
            # 4. Check if exception is related to key authorization/quota issues
            if is_key_error(e):
                print(f"[{service_name}] Key {key[:10]}... failed. Error: {e}. Trying next available key...")
                api_key_manager.mark_bad_key(key)
                last_error = e
                # Continue loop to next key
                continue
            else:
                # For non-key errors (e.g. invalid arguments, prompt blocks, etc.), raise immediately
                print(f"[{service_name}] Non-key error encountered: {e}. Raising immediately.")
                raise e

    # If the loop completes, all keys have failed
    print(f"[{service_name}] CRITICAL: All {len(api_key_manager.keys)} API keys in the Failover Pool have failed!")
    if last_error:
        raise last_error
    raise RuntimeError(f"[{service_name}] All {len(api_key_manager.keys)} API keys failed.")

# Initialize the global singleton manager
api_key_manager = ApiKeyManager()
