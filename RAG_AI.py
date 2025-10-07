import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
from chromadb.utils import embedding_functions

# -------------------------------
# 1. Setup
# -------------------------------
load_dotenv()
gemini_api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=gemini_api_key)

# Initialize Chroma client (local persistent DB)
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Create embedding function using Gemini
embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key=gemini_api_key,
    model_name="models/embedding-001"
)

# Create or load a collection
collection = chroma_client.get_or_create_collection(
    name="qwallity_docs",
    embedding_function=embedding_fn
)

# -------------------------------
# 2. Load markdown files
# -------------------------------
def load_markdown_files(directory):
    documents = []
    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        if filename.endswith(".md") and os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                documents.append((filename, content))
    return documents


directory = "./qwallity_app_doc-pkg/docs"
documents = load_markdown_files(directory)

# -------------------------------
# 3. Add documents to Chroma if not already present
# -------------------------------
existing_ids = set(collection.get()['ids']) if collection.count() > 0 else set()

new_docs = []
new_ids = []
for filename, content in documents:
    if filename not in existing_ids:
        new_docs.append(content)
        new_ids.append(filename)

if new_docs:
    collection.add(documents=new_docs, ids=new_ids)
    print(f"Added {len(new_docs)} new documents to ChromaDB.")
else:
    print("All documents already exist in ChromaDB.")

# -------------------------------
# 4. Search Function
# -------------------------------
def search_documents(question, k=3, relevance_threshold=0.67):
    results = collection.query(
        query_texts=[question],
        n_results=k
    )

    # Extract documents and distances
    if not results["documents"] or not results["documents"][0]:
        return None

    docs_with_scores = list(zip(
        results["ids"][0],
        results["documents"][0],
        results["distances"][0]
    ))

    # Apply threshold filtering
    relevant_docs = [
        (doc_id, content, dist)
        for doc_id, content, dist in docs_with_scores
        if dist <= relevance_threshold
    ]

    return relevant_docs if relevant_docs else None

# -------------------------------
# 5. Generate Answer
# -------------------------------
conversation_history = []

def generate_answer(question, user_prompt=None):
    top_documents = search_documents(question, k=3)
    relevant_texts = [doc[1] for doc in top_documents] if top_documents else []
    combined_text = "\n\n".join(relevant_texts)

    conversation_history.append({"role": "user", "content": question})
    conversation_history.append({"role": "assistant", "content": combined_text})

    if user_prompt:
        prompt = f"Using {user_prompt}, answer: {question}\n\nRelevant docs:\n{combined_text}"
    else:
        prompt = (
            f"""Question: {question}\n\nHere are some relevant documents:\n{combined_text}\n\n
            Instructions:\n
            - Provide a concise and accurate answer **based only on the above documents**.\n
            - If the question is unrelated, reply: 
              'Sorry, I can only answer questions related to the Qwallity application based on the provided information.'"""
        )

    gemini_messages = [{"role": "user", "parts": ["You are a helpful assistant."]}]
    for entry in conversation_history:
        gemini_messages.append({
            "role": "user" if entry["role"] == "user" else "model",
            "parts": [entry["content"]]
        })

    gemini_messages.append({"role": "user", "parts": [prompt]})

    # print("**********************************************************")
    # print(gemini_messages)
    # print("**********************************************************")
    model = genai.GenerativeModel("models/gemini-flash-lite-latest")
    response = model.generate_content(
        gemini_messages,
        generation_config={"max_output_tokens": 100, "temperature": 0.5}

    )
    answer = response.text.strip()
    conversation_history.append({"role": "assistant", "content": answer})
    return answer

