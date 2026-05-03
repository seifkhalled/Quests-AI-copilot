from qdrant_client import QdrantClient

qdrant_client = QdrantClient(
    url="https://7ab203dc-ba60-4c3e-8257-174e7339198b.us-west-2-0.aws.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6ZmZhNmY5ZDctOTFmNy00Yzk4LTlkNjctZDI4MmJkMWMwMGRjIn0.XZjuvQkCh0yf0Q_QwktennHX5toGyvJxqjNAgz1edms",
)

print(qdrant_client.get_collections())