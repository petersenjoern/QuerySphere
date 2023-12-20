"""Module to work with embeddings"""

from langchain.embeddings import HuggingFaceBgeEmbeddings

def get_embeddings_model(model_name: str):
    return HuggingFaceBgeEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
