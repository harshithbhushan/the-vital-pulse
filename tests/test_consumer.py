import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType, ArrayType
from datetime import datetime

@pytest.fixture(scope="session")
def spark():
    # Boot a minimal, local Spark session for testing
    return SparkSession.builder.master("local[1]").appName("VitalPulseTest").getOrCreate()

def test_anomaly_filter_with_explicit_schema(spark):
    # 1. Enforce the explicit StructType schema 
    schema = StructType([
        StructField("observation_id", StringType(), True),
        StructField("loinc_code", StringType(), True),
        StructField("metric_value", IntegerType(), True),
        StructField("event_time", TimestampType(), True)
    ])

    # 2. Mock Data: 1 Normal, 1 Tachycardia, 1 Hypoxemia
    data = [
        ("obs-1", "8867-4", 80, datetime.now()),  # Normal Heart Rate (Should be ignored)
        ("obs-2", "8867-4", 115, datetime.now()), # Tachycardia (Should be kept)
        ("obs-3", "59408-5", 85, datetime.now())  # Hypoxemia (Should be kept)
    ]

    df = spark.createDataFrame(data, schema)

    # 3. Apply the exact logic from your streaming_consumer.py
    anomalies_df = df.filter(
        ((df.loinc_code == "8867-4") & (df.metric_value >= 110)) |
        ((df.loinc_code == "59408-5") & (df.metric_value <= 89))
    )

    results = anomalies_df.collect()

    # 4. To assert the logic holds true
    assert len(results) == 2, "Filter failed to drop the normal heart rate record."
    assert results[0].observation_id == "obs-2", "Filter failed to catch Tachycardia."
    assert results[1].observation_id == "obs-3", "Filter failed to catch Hypoxemia."

def test_dead_letter_topic_routing(spark):
    # 1. Define the updated schema with the DLT catch
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
        StructField("effectiveDateTime", StringType(), True),
        StructField("_corrupt_record", StringType(), True)
    ])

    # 2. Create a mock broken JSON payload (missing closing braces and wrong data type)
    malformed_json = '{"id": "obs-99", "code": {"coding": [{"code": "8867-4"}]}, "valueQuantity": {"value": "BROKEN_STRING_NOT_INT"' 

    # 3. Read it into Spark using the corrupt record option
    df = spark.read.schema(fhir_schema) \
        .option("columnNameOfCorruptRecord", "_corrupt_record") \
        .json(spark.sparkContext.parallelize([malformed_json]))

    # 4. Assert that Spark caught the corruption
    corrupt_rows = df.filter(df._corrupt_record.isNotNull()).collect()
    
    assert len(corrupt_rows) == 1, "Filter failed to isolate the corrupt record."
    assert "BROKEN_STRING_NOT_INT" in corrupt_rows[0]._corrupt_record, "Filter failed to capture the raw malformed string."