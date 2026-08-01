# OWNEX Architecture Diagram

```mermaid
graph TB
    subgraph "Human Layer"
        H[Human Operator]
    end

    subgraph "OWNEX Core"
        EC[Event Bus]
        SC[Scheduler]
        UM[Unified Memory]
        SL[Security Layer]
    end

    subgraph "Intelligence Layer"
        ME[MERLIN]
        IE[Evolution Engine]
        RL[Recovery Engine]
    end

    subgraph "Agent Departments"
        ORCH[Orchestrator]
        ENG[Engineering]
        QUA[Quality]
        SEC[Security]
        REV[Revenue]
    end

    subgraph "Execution Layer"
        WF[Workflows]
        EX[Executors]
        PC[Platform Connectors]
    end

    subgraph "Memory Layer"
        KM[Knowledge Capture]
        FM[Feedback Loops]
        RM[Reward Models]
    end

    H -->|Strategic Direction| EC
    H -->|Approval Gates| ORCH

    EC --> SC
    EC --> UM
    EC --> SL

    SC --> ORCH
    SC --> ENG
    SC --> QUA
    SC --> SEC
    SC --> REV

    ME --> EC
    ME --> UM

    IE --> EC
    IE --> UM
    IE --> RL

    ORCH --> WF
    ENG --> WF
    QUA --> WF
    SEC --> WF
    REV --> WF

    WF --> EX
    EX --> PC

    EX --> KM
    KM --> FM
    FM --> RM
    RM --> IE

    UM --> ME
    UM --> IE

    classDef human fill:#08090A,stroke:#5E6AD2,stroke-width:2px,color:#F6F8FB
    classDef core fill:#111113,stroke:#5E6AD2,stroke-width:2px,color:#F6F8FB
    classDef intelligence fill:#1F2023,stroke:#00E39A,stroke-width:2px,color:#F6F8FB
    classDef agents fill:#111113,stroke:#5E6AD2,stroke-width:1px,color:#F6F8FB
    classDef execution fill:#1F2023,stroke:#5E6AD2,stroke-width:1px,color:#F6F8FB
    classDef memory fill:#111113,stroke:#00E39A,stroke-width:1px,color:#F6F8FB

    class H human
    class EC,SC,UM,SL core
    class ME,IE,RL intelligence
    class ORCH,ENG,QUA,SEC,REV agents
    class WF,EX,PC execution
    class KM,FM,RM memory
```

## Architecture Layers

| Layer | Responsibility | Components |
|-------|---------------|-------------|
| **Human Layer** | Strategic direction, approval gates | Human Operator |
| **OWNEX Core** | Event bus, scheduling, memory, security | Event Bus, Scheduler, Unified Memory, Security Layer |
| **Intelligence Layer** | AI assistance, evolution, recovery | MERLIN, Evolution Engine, Recovery Engine |
| **Agent Departments** | Specialized autonomous teams | Orchestrator, Engineering, Quality, Security, Revenue |
| **Execution Layer** | Workflow execution, platform integration | Workflows, Executors, Platform Connectors |
| **Memory Layer** | Learning, feedback, improvement | Knowledge Capture, Feedback Loops, Reward Models |

## Data Flow

1. **Human Direction** → Operator provides strategic goals and approval gates
2. **Event Bus** → Coordinates all system components
3. **Departments** → Autonomous agents work in parallel
4. **Execution** → Workflows run on target platforms
5. **Memory** → Outcomes captured for learning
6. **Evolution** → System improves from feedback
