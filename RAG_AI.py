import os
import faiss
import numpy as np
import uuid  # For generating a unique session ID
from dotenv import load_dotenv
import google.generativeai as genai
from text_classifier import classify_text
import logging 
load_dotenv()
gemini_api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=gemini_api_key)


# Get content from .md files
logger = logging.getLogger("qwallity_ai")

def load_markdown_files(directory):
    documents = []
    for filename in os.listdir(directory):
        with open(os.path.join(directory, filename), "r", encoding="utf-8") as f:
            content = f.read()
            documents.append((filename, content))
    return documents

# Convert text to embeddings using Gemini
# Gemini's embedding model is 'models/embedding-001'


def create_embedding(text):
    response = genai.embed_content(
        model="text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return np.array(response['embedding'])


# Load markdown files and create embeddings
directory = "./qwallity_app_doc-pkg/docs"
documents = load_markdown_files(directory)
embeddings = [create_embedding(content) for _, content in documents]

# Convert list of embeddings to a NumPy array for FAISS
embedding_matrix = np.array(embeddings).astype("float32")

# Initialize FAISS index
# Number of dimensions in each embedding
embedding_dim = embedding_matrix.shape[1]
index = faiss.IndexFlatL2(embedding_dim)

# Add embeddings to the FAISS index
index.add(embedding_matrix)

file_names = [filename for filename, _ in documents]

# Global variable to store conversation history
conversation_history = []


# k=3 to get the top 3 closest document embeddings to a query embedding.
def search_documents(question, k=3, relevance_threshold=0.67):
    # Generate embedding for the query
    query_embedding = create_embedding(
        question).astype("float32").reshape(1, -1)

    # Search in FAISS for top k nearest neighbors
    distances, indices = index.search(query_embedding, k)
    # Check if the closest document is under the relevance threshold
    if all(distance > relevance_threshold for distance in distances[0]):
        # If no document is relevant, return an empty list or a flag
        return None
    # Retrieve the corresponding documents' content (not just filenames)
    results = [(file_names[idx], documents[idx][1], distances[0][i])
               for i, idx in enumerate(indices[0])]
    return results


def generate_answer(question, user_prompt=None):
    classification_result = classify_text(question)
    question_type = classification_result["label"]
    if question_type == "greeting":
        logger.info(f"Question '{question}' classified as greeting")
        answer = "Hello! What can I help you with today?"
        return {
            "answer": answer
        }
    elif question_type == "thanks":
        logger.info(f"Question '{question}' classified as thanks")
        answer = "Thank you! Have a great day."
        return {
            "answer": answer
        }
    elif question_type == "gibberish":
        logger.info(f"Question '{question}' classified as gibberish")
        answer = "I’m not sure I understood your message. Can you try again?"
        return {
            "answer": answer
        }
    else:
        logger.info(
            f"No intent classification matched for question '{question}'. Routed to LLM."
        )
        top_documents = search_documents(question, k=3)
        relevant_texts = [doc[1]
                          for doc in top_documents] if top_documents else []
        combined_text = "\n\n".join(relevant_texts)

        conversation_history.append({"role": "user", "content": question})
        conversation_history.append(
            {"role": "assistant", "content": combined_text})

        if user_prompt:
            prompt = f"Using {user_prompt}, answer: {question}\n\nRelevant docs:\n{combined_text}"
        else:
            prompt = (
                f"""Question: {question}\n\n"
                Here are some relevant documents that may help answer the question:\n{combined_text}\n\n
                Instructions:\n
                - Provide a concise and accurate answer **based only on the above documents**.\n
                - If the question is a greeting (e.g., 'Hi', 'Hello', 'Good morning'), respond politely.\n
                - If the question is unrelated to the application or cannot be answered using the provided documents, respond with:\n
                'Sorry, I can only answer questions related to the Qwallity application based on the provided information."""
            )

        gemini_messages = [
            {"role": "user", "parts": ["You are a helpful assistant."]}]
        for entry in conversation_history:
            gemini_messages.append({
                "role": "user" if entry["role"] == "user" else "model",
                "parts": [entry["content"]]
            })

        gemini_messages.append({"role": "user", "parts": [prompt]})

        model = genai.GenerativeModel("models/gemini-flash-lite-latest")
        response = model.generate_content(
            gemini_messages,
            generation_config={"max_output_tokens": 1000, "temperature": 0.1}

        )
        input_tokens = model.count_tokens(gemini_messages).total_tokens
        answer = response.text.strip()
        output_tokens = model.count_tokens(response.text).total_tokens
        conversation_history.append({"role": "assistant", "content": answer})
        logger.info(f"Input tokens {input_tokens}, Output tokens {output_tokens}")
        return {
            "answer": answer,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
