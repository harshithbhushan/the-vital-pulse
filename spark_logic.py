import os
import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

# Forcing PySpark to use the exact Python executable from my venv
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

def test_anomaly_detection_logic():
    # 1. Initializing a local Spark session for testing
    spark = SparkSession.builder \
        .appName("VitalPulse-LogicTest") \
        .master("local[*]") \
        .getOrCreate()
    
    # MUTE THE WINDOWS HADOOP NOISE
    spark.sparkContext.setLogLevel("ERROR")
    
    # 2. Defining the Strict FHIR schema for the Json payloads
    fhir_schema = StructType([
        StructField("id", StringType(), True),
        StructField("code", StructType([
            StructField("coding", ArrayType(StructType([
                StructField("code", StringType(), True)
            ]), True))
        ]), True),
        StructField("valueQuantity", StructType([
            StructField("value", IntegerType(), True)
        ]), True),
        StructField("effectiveDateTime", StringType(), True)
    ])

    # 3. Create mock data mirroring what Kafka will eventually hand us
    mock_kafka_data = [
        ('{"id": "hr-101", "code": {"coding": [{"code": "8867-4"}]}, "valueQuantity": {"value": 85}, "effectiveDateTime": "2026-04-12T10:00:00Z"}',), # Normal HR
        ('{"id": "hr-102", "code": {"coding": [{"code": "8867-4"}]}, "valueQuantity": {"value": 145}, "effectiveDateTime": "2026-04-12T10:00:01Z"}',), # Tachycardia!
        ('{"id": "spo2-201", "code": {"coding": [{"code": "59408-5"}]}, "valueQuantity": {"value": 98}, "effectiveDateTime": "2026-04-12T10:00:02Z"}',), # Normal SpO2
        ('{"id": "spo2-202", "code": {"coding": [{"code": "59408-5"}]}, "valueQuantity": {"value": 84}, "effectiveDateTime": "2026-04-12T10:00:03Z"}',), # Hypoxemia!
    ]

    # In Spark Streaming, Kafka sends data in a column named "value"
    df_raw = spark.createDataFrame(mock_kafka_data, ["value"])

    # 4. The core pipeline: parse -> Extract -> Cast
    df_parsed = df_raw.withColumn("parsed", from_json(col("value"), fhir_schema)) \
        .select(
            col("parsed.id").alias("observation_id"),
            col("parsed.code.coding").getItem(0)["code"].alias("loinc_code"),
            col("parsed.valueQuantity.value").alias("metric_value"),
            to_timestamp(col("parsed.effectiveDateTime")).alias("event_time")
        )
    
    print("\n--- ALL INGESTED TELEMETRY ---")
    df_parsed.show(truncate=False)
    
    # 5. The Quality Gate: Detect Anomalies based on LOINC Codes
    df_anomalies = df_parsed.filter(
        ((col("loinc_code") == "8867-4") & (col("metric_value") >= 110)) | # Tachycardia condition
        ((col("loinc_code") == "59408-5") & (col("metric_value") <= 89)) # Hypoxemia condition
    )
    
    print("\n--- 🚨 CRITICAL ANOMALIES DETECTED 🚨 ---")
    df_anomalies.show(truncate=False)

if __name__ == "__main__":
    # A quick check to ensure whether Java is installed which is required for spark to run
    import shutil
    if shutil.which("java") is None:
        print("Error: Java is not installed or not in the system PATH. Please install Java to run this test.")
        print("Spark requires Java to run locally. Please install Java (JDK 8 or higher) and ensure it's added to your system PATH.")
    else:
        test_anomaly_detection_logic()
