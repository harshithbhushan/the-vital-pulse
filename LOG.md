## Day 1: Logic-First FHIR Telemetry Generation & Terminal UX Engineering
- **Goal:** Establish a strictly isolated Python development environment and engineer a localized data generator to simulate FHIR-compliant vital signs.
- **Outcome:** A successfully running `stream_vitals.py` script outputting continuous, statistically weighted HR and SpO2 JSON payloads within a secured venv workspace, featuring a locked-column terminal UI.
- **Actions:**
    - Configured an isolated Python `venv` within VS Code, anchored to the DevEnv workspace root, and upgraded the package manager.
    - Engineered `generate_fhir_heart_rate` utilizing realistic probability weights (15% critical) to simulate Tachycardia.
    - Authored `generate_fhir_spo2` from scratch, applying LOINC standard 59408-5 for Hypoxemia simulation (80-89% critical threshold).
    - Implemented a continuous `while` loop (Generator/Broadcaster pattern) simulating live telemetry.
    - Engineered the console output with fixed-width f-string padding to guarantee a clean, readable data stream.

### 🏗️ Architectural Decisions & Key Concepts
- **Logic-First Execution:** We explicitly chose to isolate and solve the data schema generation purely in Python before introducing Kubernetes, Kafka, or Spark. This "shift-left" approach prevents compounding variables and avoids the infrastructure hell of debugging data shapes and broken broker pipelines simultaneously.
- **FHIR Standard & Defeating Clinical Lag:** We structured the payload using strict HL7 FHIR Observation standards. Unlike standard batch processing, this deeply nested JSON structure guarantees data lineage (LOINC codes, UTC timestamps) in transit, enabling downstream Spark pipelines to instantly detect anomalies in memory, eliminating fatal "clinical lag."
- **The Generator/Broadcaster Pattern:** We decoupled the localized data generation (`generate_fhir_heart_rate`) from the infinite execution loop (`stream_vitals`). This ensures the generator only handles state and serialization, while the broadcaster handles velocity and network pauses (`time.sleep(1)`).
- **Multivariate Alerting:** Designed the alerting logic to evaluate both HR and SpO2 in tandem. In real hospital telemetry, a patient is critical if *either* system fails; the script accurately mirrors this boolean logic.

### ⚠️ Technical Challenges & Troubleshooting
- **Environment Isolation:** *Error:* VS Code terminal failed to auto-attach the `(venv)` prefix when opening a new integrated terminal session.
  - *Diagnosis:* The VS Code workspace was anchored to the parent directory (`VPPro`) rather than the immediate root directory containing the virtual environment (`DevEnv`). VS Code's auto-discovery requires the venv folder to sit exactly at the root of the open workspace.
  - *Fix:* Re-anchored the VS Code workspace via File > Open Folder directly to `C:\Users\harsh\Downloads\VPPro\DevEnv`. Executed a manual bypass using `.\venv\Scripts\activate` to override potential Windows execution policy silent blocks, successfully isolating the environment.
- **Terminal UI Degradation:** *Error:* The console output became jagged and unreadable due to variable-length integer strings (e.g., a 2-digit `99` vs. a 3-digit `122`).
  - *Diagnosis:* Monospaced terminal fonts require fixed character widths; differing integer lengths cause the entire trailing string to shift horizontally.
  - *Fix:* Implemented Python f-string fixed-width padding (`{bpm:>3}` and `{spo2:>3}`) to force all integers to occupy exactly 3 spaces, right-aligned, locking the data into a readable vertical column.