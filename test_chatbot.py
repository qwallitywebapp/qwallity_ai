import os
import requests
import json
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import answer_relevancy, faithfulness
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import time
import numpy
import pandas as pd


latencies = []
input_tokens = 0
output_tokens = 0

with open("RAGAS_dataset.json") as f:
    golden_data = json.load(f)
questions = [item['question'] for item in golden_data]


def add_chatbot_answer_to_dataset(question):
    global input_tokens
    global output_tokens

    start = time.time()
    try:
        chat_response = requests.post("https://qwallity-chatbot.onrender.com/api/chat",
                                    json={"message": question, "show_tokens": True},
                                    timeout=20)
        result = chat_response.json()
        answer = result.get("answer")[0]
        input_tokens_number = result.get("answer")[1]
        output_tokens_number = result.get("answer")[2]
        input_tokens += input_tokens_number
        output_tokens += output_tokens_number
    except Exception as e:  
        print(f"Error is {e}")
    finally:
        latencies.append(time.time() - start)
    for item in golden_data:
        if item['question'] == question:
            item["answer"] = answer
            item["contexts"] = []
            break

# Add chatbot answers and context to dataset
for question in questions:
    add_chatbot_answer_to_dataset(question)

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
# Connect Gemini model
llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")

# Create Dataset (RAGAS needs this format)
print(golden_data)
dataset = Dataset.from_list(golden_data)
results = evaluate(
    dataset=dataset,
    metrics=[
        answer_relevancy,
 
    ],
    llm=llm)

# calculate metrics
accuracy = float(numpy.mean(results["answer_relevancy"])) * 100
avg_latency = sum(latencies) / len(latencies)
avg_input_tokens = input_tokens / len(golden_data)
avg_output_tokens = output_tokens / len(golden_data)
throughput = 60 / avg_latency if avg_latency > 0 else 0
error_rate = 100 - accuracy
prompt_cost = (avg_input_tokens / 1_000_000)*0.10 + (avg_output_tokens / 1_000_000)* 0.40 

metrics = {
    "Accuracy (%)": round(accuracy, 2),
    "Error Rate (%)": round(error_rate, 2),
    "Latency (s)": round(avg_latency, 2),
    "Throughput (per min)": round(throughput, 2),
    "Avg Input Tokens": round(avg_input_tokens, 2),
    "Avg Output Tokens": round(avg_output_tokens, 2),
    "Prompt Cost ($)": round(prompt_cost, 4)
}
file_path = "metrics_results.xlsx"

if os.path.exists(file_path):
    # Append new results to existing file
    existing_df = pd.read_excel(file_path)
    updated_df = pd.concat([existing_df, pd.DataFrame([metrics])], ignore_index=True)
else:
    # Create a new file with headers
    updated_df = pd.DataFrame([metrics])

updated_df.to_excel(file_path, index=False)
print("Results saved to chatbot_evaluation.xlsx")
