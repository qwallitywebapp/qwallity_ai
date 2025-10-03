import os
import faiss
import numpy as np
import uuid  # For generating a unique session ID
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
gemini_api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=gemini_api_key)

# Get content from .md files
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
        model="models/embedding-001",
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
embedding_dim = embedding_matrix.shape[1]  # Number of dimensions in each embedding
index = faiss.IndexFlatL2(embedding_dim)

# Add embeddings to the FAISS index
index.add(embedding_matrix)

file_names = [filename for filename, _ in documents]

# Global variable to store conversation history
conversation_history = []

def search_documents(question, k=3, relevance_threshold=0.67):  # k=3 to get the top 3 closest document embeddings to a query embedding.
    # Generate embedding for the query
    query_embedding = create_embedding(question).astype("float32").reshape(1, -1)

    # Search in FAISS for top k nearest neighbors
    distances, indices = index.search(query_embedding, k)
    # Check if the closest document is under the relevance threshold
    if all(distance > relevance_threshold for distance in distances[0]):
        # If no document is relevant, return an empty list or a flag
        return None
    # Retrieve the corresponding documents' content (not just filenames)
    results = [(file_names[idx], documents[idx][1], distances[0][i]) for i, idx in enumerate(indices[0])]
    return results


def generate_answer(question, user_promtp=None):
    # Search for the top k documents relevant to the question
    top_documents = search_documents(question, k=3)
    # Retrieve the content of the top documents (doc[1] is the content)
    relevant_texts = [doc[1] for doc in top_documents] if top_documents else []
    combined_text = "\n\n".join(relevant_texts)
    # Maintain conversation history: Append the new question and relevant documents to the history
    conversation_history.append({"role": "user", "content": question})
    conversation_history.append({"role": "assistant", "content": combined_text})


    if user_promtp:
        prompt = f"Using {user_promtp} answer on {question} Here are some relevant documents that may help answer the question:\n{combined_text}"
    else:
        # Create the prompt to send to Gemini for generating an answer
        prompt = (
            f"Question: {question}\n\n"
            f"Here are some relevant documents that may help answer the question:\n{combined_text}\n\n"
            f"Instructions:\n"
            f"- Provide a concise and accurate answer **based only on the above documents**.\n"
            f"- If the question is a greeting (e.g., 'Hi', 'Hello', 'Good morning'), respond politely.\n"
            f"- If the question is unrelated to the application or cannot be answered using the provided documents, respond with:\n"
            f"  'Sorry, I can only answer questions related to the Qwallity application based on the provided information.'"
        )
    # 1. System message
    gemini_messages = [
        {"role": "user", "parts": ["You are a helpful assistant."]}
    ]

    # 2. Add conversation history
    for entry in conversation_history:
        if entry["role"] == "user":
            gemini_messages.append({"role": "user", "parts": [entry["content"]]})
        elif entry["role"] == "assistant":
            gemini_messages.append({"role": "model", "parts": [entry["content"]]})

    # 3. Add the new prompt as the last user message
    gemini_messages.append({"role": "user", "parts": [prompt]})

    # 4. Generate answer
    model = genai.GenerativeModel('models/gemini-2.0-flash-lite')
    response = model.generate_content(
        gemini_messages,
        generation_config={"max_output_tokens": 200, "temperature": 0.5}
    )
    answer = response.text.strip()
    conversation_history.append({"role": "assistant", "content": answer})
    return answer


