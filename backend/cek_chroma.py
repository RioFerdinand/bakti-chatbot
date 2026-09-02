import chromadb

client = chromadb.PersistentClient(path="./chroma_db_full")

collection = client.get_collection("langchain")

data = collection.get()

for i in range(len(data["ids"])):
    print("=" * 80)
    print("ID      :", data["ids"][i])
    print("Source  :", data["metadatas"][i]["source"])
    print("Page    :", data["metadatas"][i]["page"] + 1)
    print()
    print(data["documents"][i])
    print()