from langchain_ollama import OllamaLLM
import time

print("Membuat koneksi...")

llm = OllamaLLM(
    model="llama3",
)

print("Mengirim prompt...")

start = time.time()

response = llm.invoke("Halo")

end = time.time()

print("Waktu:", end - start)

print(response)