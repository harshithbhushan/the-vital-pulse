import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

def start_streaming():
    # 1. Initialize Spark with the Kafka connector package
    spark = SparkSession.builder \
        .appName("VitalPulse-AnomalyDetector") \
        .master("local[*]") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")

    # 2. Strict FHIR Schema
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

    print("🔌 Connecting to Redpanda broker at kafka-service:9092...")

    # 3. Read the Live Kafka Stream
    # Note: We use the Kubernetes internal DNS name 'kafka-service', not localhost!
    df_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka-service:9092") \
        .option("subscribe", "fhir_vitals_stream") \
        .option("startingOffsets", "latest") \
        .load()

    # 4. Parse the binary Kafka payload into JSON
    df_parsed = df_raw.selectExpr("CAST(value AS STRING) as json_payload") \
        .withColumn("parsed", from_json(col("json_payload"), fhir_schema)) \
        .select(
            col("parsed.id").alias("observation_id"),
            col("parsed.code.coding").getItem(0)["code"].alias("loinc_code"),
            col("parsed.valueQuantity.value").alias("metric_value"),
            to_timestamp(col("parsed.effectiveDateTime")).alias("event_time")
        )

    # 5. The Quality Gate: Filter for Tachycardia OR Hypoxemia
    df_anomalies = df_parsed.filter(
        ((col("loinc_code") == "8867-4") & (col("metric_value") >= 110)) |  
        ((col("loinc_code") == "59408-5") & (col("metric_value") <= 89))    
    )

    # 6. Stream the anomalies directly to the console
    query = df_anomalies.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    start_streaming()