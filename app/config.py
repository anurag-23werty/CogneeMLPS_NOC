
import os
import cognee
from dotenv import load_dotenv
import litellm

litellm.drop_params = True


load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "litellm")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral/mistral-large-latest")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")  # only needed for custom/self-hosted LLM endpoints

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "fastembed")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
# EMBEDDING_DIMENSIONS = os.getenv("EMBEDDING_DIMENSIONS")  # string from env, coerced below
EMBEDDING_ENDPOINT = os.getenv("EMBEDDING_ENDPOINT")  # override if litellm's default HF route 404s

DATASET_NAME = os.getenv("COGNEE_DATASET", "noc_incidents")


def configure_cognee() -> None:
    if not LLM_API_KEY:
        raise RuntimeError(
            "LLM_API_KEY is not set. Copy .env.example to .env and add your LLM key."
        )

    cognee.config.set_llm_provider(LLM_PROVIDER)
    cognee.config.set_llm_model(LLM_MODEL)
    cognee.config.set_llm_api_key(LLM_API_KEY)
    if LLM_ENDPOINT:
        cognee.config.set_llm_endpoint(LLM_ENDPOINT)

    cognee.config.set_embedding_provider(EMBEDDING_PROVIDER)
    cognee.config.set_embedding_model(EMBEDDING_MODEL)

    # fastembed needs no key and no dimension override (it knows its own
    # model's output size). A hosted provider needs both.
    if EMBEDDING_PROVIDER != "fastembed":
        if not EMBEDDING_API_KEY:
            raise RuntimeError(
                f"EMBEDDING_PROVIDER is '{EMBEDDING_PROVIDER}' but EMBEDDING_API_KEY is not set."
            )
        cognee.config.set_embedding_api_key(EMBEDDING_API_KEY)

        # if not EMBEDDING_DIMENSIONS:
        #     raise RuntimeError(
        #         "EMBEDDING_DIMENSIONS must be set when using a hosted embedding provider "
        #         "(384 for bge-small-en-v1.5, 1024 for bge-large-en-v1.5)."
        #     )
        # cognee.config.set_embedding_dimensions(EMBEDDING_DIMENSIONS)

        if EMBEDDING_ENDPOINT:
            cognee.config.set_embedding_endpoint(EMBEDDING_ENDPOINT)