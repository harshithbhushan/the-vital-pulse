# The Vital Pulse: Real-Time Patient Safety & FHIR Streaming Platform

An end-to-end, real-time data engineering pipeline designed to ingest simulated biometric events (Heart Rate, SpO2), detect critical medical anomalies (Tachycardia, Hypoxemia), and route FHIR-compliant payloads to an Apache Iceberg Lakehouse.

## 🏗️ Architecture & Tech Stack
- **Streaming:** Apache Kafka (Redpanda) for sub-second data-in-motion.
- **Compute:** Apache Spark Structured Streaming for distributed anomaly detection.
- **Format:** Apache Iceberg for ACID-compliant, engine-neutral storage.
- **Orchestration:** Dagster for asset-based data lineage and medical auditing.
- **Infrastructure:** Kubernetes (Minikube) for highly available, self-healing deployment.
- **CI/CD:** GitHub Actions for automated Quality Gates.

## 🚀 Execution Phases
- **Phase 1:** Logic-First FHIR Telemetry Generation (Python)
- **Phase 2:** Distributed Streaming & Storage (Kafka, Spark, Iceberg)
- **Phase 3:** The AI Bridge (Vector DB Integration for RAG)

## 📖 Development Log
Read the [LOG.md](./LOG.md) for detailed daily architectural decisions, troubleshooting steps, and technical deep-dives.