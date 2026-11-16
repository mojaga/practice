from pathlib import Path
import chromadb

# Keep the database outside the OneDrive-synced project folder.
db_path = Path.home() / "ObservIQData" / "chroma"
client = chromadb.PersistentClient(path=str(db_path))

collection = client.get_or_create_collection(
    name="installation_check",
    embedding_function=None,
)

# Explicit test vectors avoid downloading an embedding model.
collection.upsert(
    ids=["test-1"],
    documents=["Chroma installation test"],
    embeddings=[[1.0, 0.0, 0.0]],
)

result = collection.query(
    query_embeddings=[[1.0, 0.0, 0.0]],
    n_results=1,
)

assert result["ids"][0] == ["test-1"]
print(f"Chroma is working. Data location: {db_path}")

client.delete_collection("installation_check")