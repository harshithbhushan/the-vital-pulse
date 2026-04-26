import time
import random
from datetime import datetime, timezone

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


def stream_vitals():
    patient_id = "PAT-5542"
    print(f"Initializing telemetry stream for {patient_id}...\n")

    try:
        while True: # Infinite loop to simulate continuous monitoring
            hr_payload, hr_is_critical = generate_fhir_heart_rate(patient_id)
            spo2_payload, spo2_is_critical = generate_fhir_spo2(patient_id)

            # Formatting the console output for easy reading
            status_label = "CRITICAL" if hr_is_critical or spo2_is_critical else "NORMAL  "
            bpm = hr_payload['valueQuantity']['value']
            spo2 = spo2_payload['valueQuantity']['value']
            timestamp = hr_payload['effectiveDateTime']

            #print(f"[{status_label}] HR: {bpm} bpm | SPO2: {spo2}% | Timestamp: {timestamp}")
            print(f"[{status_label}] HR: {bpm:>3} bpm | SPO2: {spo2:>3}% | Timestamp: {timestamp}")

            # Simulate a 1-second interval between heartbeat readings
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStreaming stopped by user. Exiting gracefully...")

if __name__ == "__main__":
    stream_vitals()