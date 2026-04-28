import time
import random
import json
from datetime import datetime, timezone
from confluent_kafka import Producer

def generate_fhir_heart_rate(patient_id):
    # Determine state: 85% chance of normal, 15% chance of critical (Tachycardia)
    hr_is_critical = random.random() < 0.15

    # Normal HR: 60-100 bpm | Critical HR: 110-160 bpm
    heart_rate = random.randint(110, 160) if hr_is_critical else random.randint(60, 100)

    # Constructing the FHIR-compliant payload
    fhir_payload = {
        "resourceType": "Observation",
        "id": f"hr-{random.randint(10000, 99999)}",
        "status": "final",
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "8867-4",
                "display": "Heart rate"
            }]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
        "valueQuantity": {
            "value": heart_rate,
            "unit": "beats/minute",
            "system": "http://unitsofmeasure.org",
            "code": "/min"   
        }
    }
    return fhir_payload, hr_is_critical

def generate_fhir_spo2(patient_id):
    # Determine state: 90% chance of normal, 10% chance of critical (Hypoxemia)
    spo2_is_critical = random.random() < 0.10

    # Normal spo2: 95-100% | Critical spo2: 80-89%
    spo2 = random.randint(80, 89) if spo2_is_critical else random.randint(95, 100)

    # Constructing the FHIR-compliant payload
    fhir_payload = {
        "resourceType": "Observation",
        "id": f"spo2-{random.randint(10000, 99999)}",
        "status": "final",
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "59408-5",
                "display": "Oxygen saturation in arterial blood by Pulse oximetry"
            }]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
        "valueQuantity": {
            "value": spo2,
            "unit": "%",
            "system": "http://unitsofmeasure.org",
            "code": "%"
        }
    }
    return fhir_payload, spo2_is_critical

def delivery_report(err, msg):
    """Callback triggered by kafka to confirm if the message arrived successfully."""
    if err is not None:
        print(f"❌ Message delivery failed: {err}")
    else:
        print(f"✅ Message delivered successfully: {msg.topic()}/{msg.partition()}")


def stream_vitals():
    patient_id = "PAT-5542"
    topic_name = "fhir_vitals_stream"
    print(f"Initializing telemetry stream for {patient_id}...\n")

    # Kafka Producer Configuration
    kafka_config = {
        'bootstrap.servers': 'localhost:29092',
        'client.id': 'vital-pulse-generator'
    }

    # Initializing the kafka Producer
    producer = Producer(kafka_config)
    print(f"Initializing Kafka telemetry stream for {patient_id} on topic '{topic_name}'...\n")


    try:
        while True: # Infinite loop to simulate continuous monitoring
            hr_payload, hr_is_critical = generate_fhir_heart_rate(patient_id)
            spo2_payload, spo2_is_critical = generate_fhir_spo2(patient_id)

            # 1. Converting Python dictionaries to JSON strings  
            hr_json = json.dumps(hr_payload)
            spo2_json = json.dumps(spo2_payload)

            # 2. Produce/send the message to Redpanda (Kafka)
            producer.produce(topic_name, key=patient_id, value=hr_json, callback=delivery_report)
            producer.produce(topic_name, key=patient_id, value=spo2_json, callback=delivery_report)

            # 3. Trigger the delivery callbacks to process network events
            producer.poll(0)



            # Formatting the console output for easy reading
            status_label = "CRITICAL" if hr_is_critical or spo2_is_critical else "NORMAL  "
            bpm = hr_payload['valueQuantity']['value']
            spo2 = spo2_payload['valueQuantity']['value']
            timestamp = hr_payload['effectiveDateTime']

            #print(f"[{status_label}] HR: {bpm} bpm | SPO2: {spo2}% | Timestamp: {timestamp}")
            print(f"[KAFKA SENT][{status_label}] HR: {bpm:>3} bpm | SPO2: {spo2:>3}% | Timestamp: {timestamp}")

            # Simulate a 1-second interval between heartbeat readings
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStreaming stopped by user. Flushing final messages to Kafka...")
        # Ensure any remaining messages in the buffer are sent before quitting
        producer.flush()
        print("Gracefully exited.")

if __name__ == "__main__":
    stream_vitals()