import os
import time
import json
import requests
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util

# --- Initialize metrics ---
latencies = []
successes = []
total_input_tokens = 0
total_output_tokens = 0

# --- Load golden dataset ---
with open("dataset.json", "r", encoding="utf-8") as f:
    golden_data = json.load(f)
questions = [item["question"] for item in golden_data]

# --- Define chatbot query helper ---


def add_chatbot_answer_to_dataset(question):
    global total_input_tokens, total_output_tokens

    start_time = time.perf_counter()
    answer = ""
    in_tokens = 0
    out_tokens = 0
    success = False

    try:
        response = requests.post(
            "https://qwallity-ai-chatbot.fly.dev/api/chat",
            json={"message": question, "show_details": True},
            timeout=20
        )
        response.raise_for_status()
        result = response.json()

        # Safely unpack the answer structure
        answer_data = result.get("answer", {})

        answer = answer_data.get("answer", "")
        in_tokens = answer_data.get("input_tokens", 0)
        out_tokens = answer_data.get("output_tokens", 0)

        # Update global accumulators
        total_input_tokens += in_tokens
        total_output_tokens += out_tokens
        success = bool(answer)

    except Exception as e:
        print(f"[ERROR] {e}")

    finally:
        latencies.append(time.perf_counter() - start_time)
        successes.append(success)

    # Update dataset dictionary so data persists for the evaluation loop
    for item in golden_data:
        if item["question"] == question:
            item["answer"] = answer
            item["input_tokens"] = in_tokens
            item["output_tokens"] = out_tokens
            item["contexts"] = []
            break


# --- Query chatbot for all questions ---
for question in questions:
    add_chatbot_answer_to_dataset(question)
    time.sleep(0.5)

# --- Evaluate semantic similarity ---
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Pre-calculate embeddings for better performance
semantic_scores = []
for item in golden_data:
    # Handle empty answers to prevent errors
    ans_text = item.get("answer", "")
    if not ans_text:
        semantic_scores.append(0.0)
        continue

    gt_emb = embedder.encode(item["expected_result"], convert_to_tensor=True)
    ans_emb = embedder.encode(ans_text, convert_to_tensor=True)
    similarity = util.cos_sim(gt_emb, ans_emb).item()
    semantic_scores.append(float(np.clip(similarity, 0, 1)))

# --- Calculate metrics ---
results = []

for i in range(len(golden_data)):
    item = golden_data[i]
    similarity = semantic_scores[i]
    semantic_similarity_pct = similarity * 100

    latency = latencies[i]
    success = successes[i]
    throughput = 60 / latency if latency > 0 else 0

    # These now exist because we saved them in the helper function
    in_tokens = item.get("input_tokens", 0)
    out_tokens = item.get("output_tokens", 0)

    prompt_cost = (
        (in_tokens / 1_000_000) * 0.10 +
        (out_tokens / 1_000_000) * 0.40
    )

    results.append({
        "Question": item["question"],
        "Success": success,
        "Semantic Similarity (%)": round(semantic_similarity_pct, 2),
        "Latency (s)": round(latency, 2),
        "Estimated Throughput (per min)": round(throughput, 2),
        "Input Tokens": in_tokens,
        "Output Tokens": out_tokens,
        "Prompt Cost ($)": round(prompt_cost, 6),
    })

results_df = pd.DataFrame(results)
results_df.to_excel("metrics_per_question.xlsx", index=False)

print(
    f"[INFO] Per-question metrics saved. Total Input Tokens: {total_input_tokens}")
