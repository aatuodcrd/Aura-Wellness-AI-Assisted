# Aura Wellness Platform Architecture Documentation
**Version:** 3.4
**Last Updated:** February 1, 2024
**Author:** Backend Architecture Guild

---

## 1. System Overview

Aura Wellness operates on a cloud-native, microservices-based architecture hosted primarily on **AWS (Amazon Web Services)**. The system is designed to handle high concurrency (1M+ DAU), real-time data streaming (biofeedback), and low-latency content delivery.

### 1.1 High-Level Diagram
```mermaid
graph TD
    Client[Mobile/Web Client] -->|HTTPS/WSS| CDN[CloudFront CDN]
    CDN --> LB[Application Load Balancer]
    LB --> Gateway[API Gateway / Kong]
    
    subgraph "Core Services"
        Gateway --> Auth[Auth Service (Go)]
        Gateway --> Users[User Profile Service (Node.js)]
        Gateway --> Content[Content CMS (Python/Django)]
        Gateway --> Payment[Payment Service (Java/Spring)]
    end
    
    subgraph "AI & Data Plane"
        Gateway --> Ingest[Data Ingestion (FastAPI)]
        Ingest --> Kafka[Apache Kafka]
        Kafka --> Processor[Stream Processor (Flink)]
        Processor --> VectorDB[Qdrant Vector DB]
        Processor --> TimeSeries[TimescaleDB]
        
        VectorDB --> RecSys[Recommendation Engine (Python)]
    end
    
    subgraph "Storage"
        Auth --> RDS_Auth[RDS Postgres]
        Users --> RDS_Users[RDS Postgres]
        Content --> S3[S3 Media Bucket]
        RecSys --> Redis[Redis Cache]
    end
```

---

## 2. Core Components

### 2.1 API Gateway
*   **Technology:** Kong Gateway
*   **Responsibility:** Authentication (JWT validation), Rate Limiting (1000 req/min/user), Request Routing, and Logging.
*   **Endpoints:** All public traffic enters through `api.aurawellness.com`.

### 2.2 Auth Service (`auth-svc`)
*   **Language:** Go (Golang)
*   **Protocol:** gRPC (internal), REST (external)
*   **Database:** PostgreSQL (Users, Roles, Permissions)
*   **Key Features:**
    *   Handles OAuth2 login (Google, Apple).
    *   Issues short-lived Access Tokens (15 min) and Refresh Tokens (7 days).
    *   Implements RBAC (Role-Based Access Control) for internal admin tools.

### 2.3 User Profile Service (`user-svc`)
*   **Language:** TypeScript (Node.js/NestJS)
*   **Responsibility:** Manages user settings, preferences, streaks, and gamification logic.
*   **Data Model:** Stores user profile in Postgres, but caches "Streak" and "Daily Status" in Redis for fast read access during app launch.

### 2.4 Content Delivery (`cms-svc`)
*   **Language:** Python (Django Rest Framework)
*   **Responsibility:** Catalog of meditations, sleep stories, and music.
*   **Storage:**
    *   Metadata (Title, Duration, Tags) stored in Postgres.
    *   Binary Files (Audio/Video) stored in AWS S3 with CloudFront Signed URLs.
*   **Search:** Uses Elasticsearch for full-text search of content titles and descriptions.

---

## 3. The "Bio-Sync" Pipeline (Real-Time Data)

This is the most critical subsystem for Project Alpha, handling real-time heart rate and HRV data.

### 3.1 Ingestion
*   Wearable devices (Apple Watch) send batched JSON payloads via WebSocket to `wss://stream.aurawellness.com`.
*   **Service:** `ingest-svc` (FastAPI + Websockets).
*   **Throughput:** Capable of handling 50,000 concurrent socket connections.

### 3.2 Processing
*   Data is pushed to **Apache Kafka** topic `bio-sensor-raw`.
*   **Apache Flink** jobs consume this topic to:
    1.  Cleanse noise.
    2.  Calculate rolling average HRV (1-minute window).
    3.  Detect "Stress Events" (Sudden HR spike + HRV drop).
*   Processed events are written to **TimescaleDB** for historical reporting.

### 3.3 Dynamic Response
*   If a "Stress Event" is detected, Flink triggers a webhook to `recommendation-engine`.
*   The engine queries **Qdrant** (Vector DB) for content vectors similar to "Calming," "Crisis," "Panic attack."
*   The top result is pushed back to the client via the WebSocket to suggest an immediate "Emergency Calm" session.

---

## 4. Infrastructure & DevOps

### 4.1 Deployment
*   **Containerization:** All services are Dockerized.
*   **Orchestration:** Kubernetes (EKS).
    *   **Node Pools:** Spot instances for worker nodes (cost saving), On-demand for stateful sets.
*   **CI/CD:** GitHub Actions.
    *   Push to `main` -> Run Unit/Integration Tests -> Build Docker Image -> Deploy to `Staging`.
    *   Manual approval -> Deploy to `Production`.

### 4.2 Observability
*   **Metrics:** Prometheus + Grafana (Dashboards for Latency, Error Rate, Saturation).
*   **Logs:** ELK Stack (Elasticsearch, Logstash, Kibana).
*   **Tracing:** OpenTelemetry + Jaeger. Every request has a `X-Trace-Id` propagated across microservices.

### 4.3 Disaster Recovery (DR)
*   **RPO (Recovery Point Objective):** 5 minutes (Database snapshots).
*   **RTO (Recovery Time Objective):** 1 hour.
*   **Strategy:** Active-Passive. A secondary environment is provisioned in `us-east-1` (Primary is `us-west-2`) with database replication enabled. In case of primary region failure, DNS is rerouted via Route53.

---

## 5. Security Protocols

1.  **Encryption at Rest:** All EBS volumes and S3 buckets are encrypted with AWS KMS keys.
2.  **Encryption in Transit:** TLS 1.3 enforced for all internal and external communication.
3.  **Secret Management:** No secrets in code. We use AWS Secrets Manager and inject them as environment variables at runtime.
4.  **Penetration Testing:** Conducted quarterly by an external firm (Rapid7).

---
*For more details on specific services, refer to their respective repositories in GitHub.*
