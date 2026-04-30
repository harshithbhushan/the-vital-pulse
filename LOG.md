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


## Day 2: CI/CD Quality Gate & PySpark Anomaly Logic Validation
- **Goal:** Establish an automated CI/CD pipeline for code validation and engineer the distributed PySpark logic for real-time anomaly detection.
- **Outcome:** Successfully implemented a GitHub Actions workflow with a Flake8 Quality Gate. Authored and validated the core PySpark parsing/filtering DataFrame logic, pivoting to containerized Linux deployment after isolating Windows OS Py4J socket limitations.
- **Actions:**
    - Configured a `.github/workflows/python-lint.yml` CI pipeline to spin up Ubuntu containers and enforce syntax standards on every push.
    - Locked dependencies using `requirements.txt` to guarantee deterministic builds across dev, test, and production environments.
    - Authored `spark_logic.py`, defining a strict `StructType` schema to unpack nested FHIR JSON payloads natively.
    - Engineered PySpark DataFrame `.filter()` conditions to isolate Tachycardia (HR >= 110) and Hypoxemia (SpO2 <= 89).
    - Executed a strategic OS-environment pivot to Kubernetes upon validating the Spark logic execution to achieve full environment parity.

### 🏗️ Architectural Decisions & Key Concepts
- **Deterministic Builds:** By explicitly pinning `flake8>=7.0.0` and `pyspark>=3.5.0` in a `requirements.txt` manifest, we prevent the CI pipeline from pulling unverified future versions. This guarantees environment parity—ensuring the testing server runs the exact same software ecosystem as the local machine and production cluster.
- **The CI/CD "Kill Switch" vs. "Warning Track":** Configured the YAML workflow with two distinct Flake8 linting passes. The first pass acts as a strict kill switch (exit code 1) for fatal syntax errors, blocking merges. The second pass acts as a warning track (`--exit-zero`), flagging style violations (like line length) without crashing the pipeline.
- **Strict Schema Enforcement:** Rather than relying on Spark's `inferSchema` (which is computationally expensive and requires full-table scans), we explicitly defined the FHIR nested JSON structure (`StructType`, `ArrayType`). This guarantees deterministic parsing in a high-velocity streaming context.
- **The JVM Monopoly & Py4J Abstraction:** Acknowledged that PySpark operates via the Py4J bridge, translating Python commands to Java bytecode for execution on the Java Virtual Machine (JVM). Understanding this architecture allowed us to diagnose crashes as JVM memory/socket failures rather than Python logic failures.
- **Environment Parity & Timeboxing:** When local testing hit severe OS-level bottlenecks, we evaluated the stack trace. Because the script successfully executed the parsing and filtering logic but failed at the Py4J `showString` Windows socket transfer, we deemed the logic sound. We chose to halt local Windows workarounds in favor of native Linux execution (Minikube) to mirror production environments.

### ⚠️ Technical Challenges & Troubleshooting
- **GitHub Actions Dependency Cache Miss:** - *Error:* `No file matched to [**/requirements.txt or **/pyproject.toml]`
  - *Diagnosis:* The CI pipeline attempted to cache pip dependencies but failed because a manifest did not exist to hash against.
  - *Fix:* Created a strict `requirements.txt` and updated the YAML to execute `pip install -r requirements.txt`.
- **Global vs. Virtual Environment Ghosting:**
  - *Error:* `ModuleNotFoundError: No module named 'pyspark'` despite terminal indicating successful installation.
  - *Diagnosis:* The bare `pip install` command resolved to the global Windows Python path, ignoring the active VS Code (venv).
  - *Fix:* Enforced explicit module targeting using `python -m pip install -r requirements.txt`.
- **PySpark OS Pathing & Python3 Alias:**
  - *Error:* `Cannot run program "python3": CreateProcess error=2`
  - *Diagnosis:* PySpark defaults to Linux `python3` naming conventions, failing to locate the Windows `python.exe` executable inside the virtual environment.
  - *Fix:* Dynamically routed the Spark driver using `os.environ['PYSPARK_PYTHON'] = sys.executable`.
- **Java 25 Security vs. PySpark Py4J Bridge:**
  - *Error:* JVM memory access violations resulting in Spark engine crash.
  - *Diagnosis:* Java 25 natively blocks `sun.misc.Unsafe` memory access, which Spark 3.5 relies heavily upon for worker communication.
  - *Fix:* Downgraded the system JVM to Eclipse Temurin JDK 17 (LTS), stabilizing the core Spark engine.
- **Python 3.12 Py4J Socket Crash on Windows:**
  - *Error:* `java.io.EOFException: Python worker exited unexpectedly (crashed).`
  - *Diagnosis:* With the JVM stabilized, the Python 3.12 worker crashed upon rendering the DataFrame (`showString`). This is a known threading/socket bug between Python 3.12 and Py4J operating strictly on Windows OS.
  - *Fix:* Validated the code logic via the stack trace (which proved successful execution up to the print statement) and aborted local Windows debugging in favor of Phase 2 containerized Linux deployment.


## Day 3: Infrastructure-as-Code & Distributed Streaming (Minikube + Kafka)
- **Goal:** Pivot from local Windows execution to a containerized, production-grade Linux environment to support distributed message brokering and stream processing.
- **Outcome:** Successfully deployed a local Minikube cluster, provisioned a Redpanda (Kafka) broker, and connected an asynchronous Python producer to a native PySpark streaming consumer container.
- **Actions:**
    - Initialized a Minikube cluster using the Docker (WSL2) driver to bypass host OS limitations.
    - Authored Kubernetes manifests (`Deployment`, `Service`, `Job`) to provision the Redpanda broker and the Spark consumer.
    - Upgraded `stream_vitals.py` using `confluent_kafka` to asynchronously produce FHIR payloads to the broker, implementing a `delivery_report` callback to monitor network latency.
    - Containerized the PySpark anomaly logic using a lightweight Python 3.11/Java 17 Docker image and deployed it directly into the Minikube registry.

### 🏗️ Architectural Decisions & Key Concepts
- **Redpanda over Apache Kafka:** Selected Redpanda for the local message broker to eliminate the JVM overhead and Zookeeper dependencies of native Kafka, ensuring stable operation within a local Minikube environment while maintaining 100% Kafka API compatibility.
- **Declarative Infrastructure:** Opted for a `Deployment` over a basic `Pod` for Redpanda, ensuring Kubernetes actively monitors and respawns the broker if it crashes. Enforced strict hardware constraints (`--smp=1`, `--memory=1G`) via YAML args to prevent the broker from starving the Minikube node.
- **Asynchronous Publishing & Zero Data Loss:** Configured the Python producer to push data without waiting for synchronous network ACKs, utilizing background polling (`producer.poll(0)`) to process delivery receipts and maximize throughput. Implemented a fatal termination trap (`producer.flush()`) to guarantee all buffered messages are successfully transmitted before the script exits.
- **Deterministic Partitioning:** Enforced message ordering by publishing payloads with a specific key (`patient_id`), guaranteeing all telemetry for a given patient hashes to the exact same Kafka partition.

### ⚠️ Technical Challenges & Troubleshooting
- **Kubernetes API Versioning:**
  - *Error:* `no matches for kind "Deployment" in version "api/v1"`
  - *Diagnosis:* Attempted to deploy the Redpanda broker using the base `v1` API group.
  - *Fix:* Corrected the manifest to utilize the `apps/v1` API group required for `Deployment` resources.
- **The "Advertised Listener" Trap (Split-Brain DNS):**
  - *Error:* `TimeoutException: Timed out waiting for a node assignment` within the Spark container.
  - *Diagnosis:* The Redpanda broker defaulted to advertising `127.0.0.1` as its address. While this successfully routed traffic from the host Windows machine via port-forwarding, it caused the Spark container (running inside Minikube) to attempt to route traffic to its own internal localhost rather than the broker.
  - *Fix:* Implemented a split-brain listener configuration (`--kafka-addr` and `--advertise-kafka-addr`). Configured an internal listener (`kafka-service:9092`) for intra-cluster Spark traffic, and an external listener (`localhost:29092`) for host-machine Python traffic.


## Day 4: The Storage Layer & Medallion Architecture (MinIO + Apache Iceberg)
- **Goal:** Evolve the real-time stream into a durable Lakehouse by routing intercepted anomalies from the Kafka broker into S3-compatible object storage using an ACID-compliant table format.
- **Outcome:** Successfully deployed a local MinIO object store natively in Kubernetes and upgraded the PySpark consumer to write micro-batches directly into an Apache Iceberg table.
- **Actions:**
    - Deployed MinIO natively via Kubernetes Infrastructure-as-Code after diagnosing a broken image manifest in the official Bitnami Helm chart.
    - Configured port-forwarding to access the MinIO API (`9000`) and the Web Console (`9001`), manually provisioning the `vital-pulse-lakehouse` S3 bucket.
    - Injected AWS S3 (`hadoop-aws`) and Iceberg (`iceberg-spark-runtime`) Maven packages into the Spark container.
    - Authored PySpark SQL commands to dynamically provision a `lakehouse.medical.critical_vitals_v2` table.
    - Updated the Spark Structured Streaming sink to output `.parquet` files governed by Iceberg metadata with a 5-second trigger.

### 🏗️ Architectural Decisions & Key Concepts
- **Lakehouse over Data Warehouse:** Selected Apache Iceberg on MinIO rather than a traditional relational database. This allows for massive, cheap storage of raw FHIR JSONs while maintaining ACID transactional guarantees and schema enforcement, setting up the "Silver/Gold" layer of the Medallion Architecture.
- **Infrastructure-as-Code (IaC) vs. Package Managers:** Pivoted from Helm to raw Kubernetes manifests for the MinIO deployment to ensure absolute control over image tags and container configuration, avoiding upstream open-source registry failures.

### ⚠️ Technical Challenges & Troubleshooting
- **Helm Repository Image Deprecation:**
  - *Error:* `manifest unknown` for Bitnami MinIO image during Helm install.
  - *Diagnosis:* The upstream Helm chart referenced a deprecated or deleted Docker tag.
  - *Fix:* Uninstalled the broken Helm release and authored a native `minio.yaml` Deployment and Service using the stable `minio/minio:latest` image.
- **Spark Structured Streaming Partition Limitation:**
  - *Error:* `days(event_time) is not currently supported`
  - *Diagnosis:* While Apache Iceberg supports hidden partitioning (`days()`), PySpark's Structured Streaming V2 Data Source API currently lacks support for dynamic time transformations during micro-batch appends.
  - *Fix:* Simplified the Iceberg schema to an unpartitioned table, which is perfectly performant for the local data volume.
- **The Checkpoint Cache Trap:**
  - *Error:* Spark continually crashed with the partition error even after the Python code was corrected and the Docker image rebuilt.
  - *Diagnosis:* Spark reads its `checkpointLocation` in S3 *before* executing code to resume state. The broken partition rules from the first run were permanently cached in the MinIO checkpoint files.
  - *Fix:* Executed the "Nuclear Option." Purged the corrupted MinIO directories and bumped the application versioning (`critical_vitals_v2` and Docker tag `v2`) to force the cluster to generate entirely fresh, untainted metadata and states.

