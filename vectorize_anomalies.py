import os
import sys
from pyspark.sql import SparkSession
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
os.environ['HADOOP_HOME'] = 'C:\\hadoop'

def build_ai_bridge():
    # 1. Connecting to Qdrant (via port-forward bridge)
    print("🧠 Connecting to Qdrant Vector Database...")
    qdrant = QdrantClient("http://localhost:6333")
    
    collection_name = "clinical_anomalies"
    
    # MiniLM creates vectors with exactly 384 dimensions
    if not qdrant.collection_exists(collection_name):
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    # 2. Loading the Embedding Model
    print("🤖 Loading Open-Source Embedding Model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # 3. Connecting to the Iceberg Lakehouse (via Windows localhost)
    print("🧊 Reading data from Iceberg Lakehouse...")
    spark = SparkSession.builder \
        .appName("VitalPulse-AI-Bridge") \
        .master("local[*]") \
        .config("spark.jars.packages", 
                "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,"
                "org.apache.hadoop:hadoop-aws:3.3.4,"
                "com.amazonaws:aws-java-sdk-bundle:1.12.262") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.lakehouse.type", "hadoop") \
        .config("spark.sql.catalog.lakehouse.warehouse", "s3a://vital-pulse-lakehouse/warehouse") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "admin") \
        .config("spark.hadoop.fs.s3a.secret.key", "password123") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")

    # Reading the anomalies table
    try:
        df = spark.table("lakehouse.medical.critical_vitals_v2")
        records = df.collect()
    except Exception as e:
        print(f"❌ Error reading Lakehouse: {e}")
        return

    if not records:
        print("⚠️ No records found in the Lakehouse. Ensure the streaming pipeline has processed data.")
        return

    # 4. To vectorize and load into Qdrant
    print(f"🚀 Vectorizing {len(records)} medical anomalies...")
    points = []
    
    for idx, row in enumerate(records):
        # Translating the raw tabular data into a human-readable clinical sentence
        status = "Tachycardia" if row.loinc_code == "8867-4" else "Hypoxemia"
        metric_name = "Heart rate" if status == "Tachycardia" else "SpO2"
        
        clinical_context = f"Patient anomaly detected: {status}. The patient's {metric_name} was {row.metric_value} at {row.event_time}."
        
        # Converting the sentence into a mathematical vector
        vector = model.encode(clinical_context).tolist()
        
        # Package it as a Point for Qdrant (Vector + Original Metadata)
        points.append(PointStruct(
            id=idx + 1,
            vector=vector,
            payload={
                "observation_id": row.observation_id,
                "anomaly_type": status,
                "metric_value": row.metric_value,
                "event_time": str(row.event_time),
                "context": clinical_context
            }
        ))

    # Pushing to the Vector Database
    qdrant.upsert(
        collection_name=collection_name,
        points=points
    )
    
    print("✅ Successfully built the AI Bridge! Vectors are live in Qdrant.")

if __name__ == "__main__":
    build_ai_bridge()