import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, expr
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType

def start_streaming():
    # 1. Initialize Spark 
    print("🧊 Booting Spark with Iceberg and S3 modules...")
    spark = SparkSession.builder \
        .appName("VitalPulse-LakehouseWriter") \
        .master("local[*]") \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,"
                "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.5.0,"
                "org.apache.hadoop:hadoop-aws:3.3.4,"
                "com.amazonaws:aws-java-sdk-bundle:1.12.262") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.lakehouse.type", "hadoop") \
        .config("spark.sql.catalog.lakehouse.warehouse", "s3a://vital-pulse-lakehouse/warehouse") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "admin") \
        .config("spark.hadoop.fs.s3a.secret.key", "password123") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")

    # 2. Setup the V2 Iceberg Table 
    print("🏗️ Ensuring Lakehouse schema exists...")
    spark.sql("CREATE NAMESPACE IF NOT EXISTS lakehouse.medical")
    
    spark.sql("""
        CREATE TABLE IF NOT EXISTS lakehouse.medical.critical_vitals_v2 (
            observation_id STRING,
            loinc_code STRING,
            metric_value INT,
            event_time TIMESTAMP
        ) USING iceberg
    """)

    # 3. Strict FHIR Schema WITH DLT Catch
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
        StructField("_corrupt_record", StringType(), True) # ADDED: Catches broken JSON
    ])

    print("🔌 Connecting to Redpanda broker at kafka-service:9092...")

    # 4. Read the Live Kafka Stream
    df_raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka-service:9092") \
        .option("subscribe", "fhir_vitals_stream") \
        .option("startingOffsets", "latest") \
        .load()

    # 5. Parse the binary Kafka payload
    # Using 'columnNameOfCorruptRecord' option so Spark knows where to put bad data
    df_parsed = df_raw.selectExpr("CAST(value AS STRING) as json_payload") \
        .withColumn("parsed", from_json(col("json_payload"), fhir_schema, {"columnNameOfCorruptRecord": "_corrupt_record"}))

    # ---------------------------------------------------------
    # NEW DLT ARCHITECTURE: SPLIT THE STREAM
    # ---------------------------------------------------------
    
    # Stream A: Valid Records
    df_valid = df_parsed.filter(col("parsed._corrupt_record").isNull()) \
        .select(
            col("parsed.id").alias("observation_id"),
            col("parsed.code.coding").getItem(0)["code"].alias("loinc_code"),
            col("parsed.valueQuantity.value").alias("metric_value"),
            to_timestamp(col("parsed.effectiveDateTime")).alias("event_time")
        )

    # Stream B: Corrupt Records (Dead-Letter Topic)
    df_corrupt = df_parsed.filter(col("parsed._corrupt_record").isNotNull()) \
        .select(
            col("parsed._corrupt_record").alias("value"), # Kafka requires payload in 'value' col
            expr("CAST(current_timestamp() AS STRING) as key")
        )

    # 6. The Quality Gate: Filter for anomalies on the VALID stream only
    df_anomalies = df_valid.filter(
        ((col("loinc_code") == "8867-4") & (col("metric_value") >= 110)) |  
        ((col("loinc_code") == "59408-5") & (col("metric_value") <= 89))    
    )

    print("💾 Starting streams: Iceberg Lakehouse & Redpanda DLT...")

    # 7. Write Valid Stream to Iceberg
    query_iceberg = df_anomalies.writeStream \
        .format("iceberg") \
        .outputMode("append") \
        .trigger(processingTime="5 seconds") \
        .option("path", "lakehouse.medical.critical_vitals_v2") \
        .option("checkpointLocation", "s3a://vital-pulse-lakehouse/checkpoints/critical_vitals_v2") \
        .start()

    # 8. Write Corrupt Stream back to Redpanda (The Dead-Letter Topic)
    query_dlt = df_corrupt.writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka-service:9092") \
        .option("topic", "vital-pulse-dlt") \
        .option("checkpointLocation", "s3a://vital-pulse-lakehouse/checkpoints/vital_pulse_dlt") \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == "__main__":
    start_streaming()