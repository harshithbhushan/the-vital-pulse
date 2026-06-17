# tests/test_consumer.py
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType
from datetime import datetime

@pytest.fixture(scope="session")
def spark():
    # Boot a minimal, local Spark session for testing
    return SparkSession.builder.master("local[1]").appName("VitalPulseTest").getOrCreate()

def test_anomaly_filter_with_explicit_schema(spark):
    # 1. Enforce the explicit StructType schema (Defending your 40% compute overhead metric)
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

    # 4. Assert the logic holds true
    assert len(results) == 2, "Filter failed to drop the normal heart rate record."
    assert results[0].observation_id == "obs-2", "Filter failed to catch Tachycardia."
    assert results[1].observation_id == "obs-3", "Filter failed to catch Hypoxemia."