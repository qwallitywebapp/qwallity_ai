import os
import openai
import faiss
import numpy as np
import uuid  # For generating a unique session ID
from dotenv import load_dotenv

load_dotenv('data.env')
openai_key = os.getenv('api_key')
openai.api_key = openai_key


# Create a unique session ID for each interaction or user session
def create_session_id():
    return str(uuid.uuid4())  # Generates a new unique session ID


# Get content from .md files
def load_markdown_files(directory):
    documents = []
    for filename in os.listdir(directory):
        with open(os.path.join(directory, filename), "r", encoding="utf-8") as f:
            content = f.read()
            documents.append((filename, content))
    return documents


# Convert text to embeddings
def create_embedding(text):
    response = openai.Embedding.create(input=text, model="text-embedding-ada-002")
    return np.array(response['data'][0]['embedding'])


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


def generate_answer(question):
    # Search for the top k documents relevant to the question
    top_documents = search_documents(question, k=3)
    # Retrieve the content of the top documents (doc[1] is the content)
    relevant_texts = [doc[1] for doc in top_documents]
    combined_text = "\n\n".join(relevant_texts)
    # Maintain conversation history: Append the new question and relevant documents to the history
    conversation_history.append({"role": "user", "content": question})
    conversation_history.append({"role": "assistant", "content": combined_text})
    if top_documents is None:
        prompt = f"Question: {question}"
    else:
        # Create the prompt to send to OpenAI for generating an answer
        prompt = f"Question: {question}\n\n" \
            f"Here are some relevant documents that may help answer the question:\n{combined_text}\n\n" \
            f"Based on the above documents, please provide a concise, accurate answer to the question above."

# Add the conversation history and the new prompt to the API call
    response = openai.ChatCompletion.create(
        model="gpt-4",  # Or "gpt-3.5-turbo" for a cheaper alternative
        messages=[
            {"role": "system", "content": "You are a helpful assistant."}
        ] + conversation_history + [{"role": "user", "content": prompt}],  # Correctly combine the lists
        max_tokens=200,  # Limit the response length
        temperature=0.5,  # Controls the randomness of the output
    )

    # Extract the generated answer from the response
    answer = response['choices'][0]['message']['content'].strip()
    # Update the conversation history with the new response
    conversation_history.append({"role": "assistant", "content": answer})

    return answer


