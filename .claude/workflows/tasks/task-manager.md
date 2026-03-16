# Task Manager

> Responsible for coordinating the entire multi-Agent workflow, managing task states and role collaboration

## Overview

**Type**: Workflow orchestration and task management

**Responsibilities**:
- Initialize tasks and assign to correct stages
- Manage task state transitions
- Invoke corresponding Agents to execute tasks
- Coordinate multi-role collaboration
- Record execution logs

## Usage

### Initiate New Task

```
/task-manager

Task: [task description]
Type: [feature/bugfix/optimization]
Priority: [P0/P1/P2/P3]
```

### Check Task Status

```
/task-manager status [task-id]
```

### Continue Task

```
/task-manager continue [task-id]
```

### List Tasks

```
/task-manager list
/task-manager list -status in_progress
```

## Core Functions

### 1. Task Initialization

Receive user task request, perform initial analysis:

```yaml
Task Type Recognition:
  feature: Feature Workflow
  bugfix: Bugfix Workflow
  Optimization: Optimization Workflow

Priority Assignment:
  P0: Execute immediately
  P1: Complete within this week
  P2: Complete within this month
  P3: Complete within this quarter
```

### 2. Stage Management

Start corresponding workflow based on task type:

| Task Type | Workflow |
|-----------|----------|
| feature | Product Planning → Technical Design → Development → Quality Review |
| bugfix | Technical Assessment → Fix Execution → Testing → Review |
| optimization | Technical Review → Implementation → Verification |

### 3. Agent Scheduling

Schedule corresponding Agents based on current stage:

```yaml
Stage_ProductPlanning:
  Execute: Senior PM
  Review: Director
  Output: Product Spec

Stage_TechnicalDesign:
  Execute: Tech Manager
  Review: Senior Architect
  Output: Technical Design

Stage_Development:
  Execute: Tech Manager
  Review: Tech Manager
  Output: Code Implementation

Stage_QualityReview:
  Execute: [Senior Architect, Senior Fullstack, Senior PM]
  Review: Director
  Output: Final Review Report
```

### 4. State Management

Manage complete task lifecycle:

```
PENDING → IN_PROGRESS → PENDING_REVIEW → APPROVED/REJECTED → ...
```

### 5. Logging

Record execution logs for each stage:

```yaml
Log Contents:
  - Executor
  - Start/End time
  - Input/Output
  - Review comments
  - State changes
```

## Execution Flow

### Main Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Receive User Task                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Analyze Task                                                 │
│ - Identify task type                                             │
│ - Assign priority                                                │
│ - Determine workflow                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Execute Current Stage                                         │
│ - Invoke execution Agent                                         │
│ - Collect outputs                                                │
│ - Invoke review Agent                                            │
│ - Decide next step based on review result                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌───────────────────────────────────────────────┐
                    │ 4. Loop until complete                      │
                    │ - Approved: Proceed to next stage            │
                    │ - Needs Revision: Return for revision       │
                    │ - Rejected: Task terminated                 │
                    └───────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Output Final Report                                           │
│ - Summarize all stage outputs                                    │
│ - Output execution statistics                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Exception Handling

| Exception | Handling |
|-----------|----------|
| Agent execution failed | Log error, retry |
| Review timeout | Auto-remind reviewer |
| Task blocked | Log blocking reason, wait for resolution |
| Review rejected | Return to previous stage for revision |

## Data Structures

### Task Object

```yaml
Task:
  id: string
  title: string
  description: string
  type: feature | bugfix | optimization
  priority: P0 | P1 | P2 | P3
  state: PENDING | IN_PROGRESS | PENDING_REVIEW | ...
  current_stage: 1 | 2 | 3 | 4
  created_at: datetime
  updated_at: datetime
  outputs:
    product_spec: path
    technical_design: path
    code_implementation: path
    review_report: path
```

### Stage Object

```yaml
Stage:
  id: number
  name: string
  execute_role: string
  review_role: string
  state: pending | in_progress | approved | rejected
  start_time: datetime
  end_time: datetime
  output: path
  review_comments: string
```

## Output Formats

### Task Created Successfully

```
✅ Task Created

Task ID: TASK-20240308-001
Title: [task title]
Type: [feature/bugfix/optimization]
Priority: [P0/P1/P2/P3]
Current Stage: Product Planning

Next Step: Director starts strategic analysis
```

### Stage Completed

```
✅ Stage [1] Product Planning Completed

Executor: Senior PM
Output: docs/product/product-spec-20240308.md
Review: Approved

Next Step: Proceed to Stage 2 - Technical Design
```

### Task Completed

```
✅ Task Completed

Task ID: TASK-20240308-001
Title: [task title]
Completed At: 2024-03-08 18:30

Execution Statistics:
- Stage 1 Product Planning: 2 hours
- Stage 2 Technical Design: 3 hours
- Stage 3 Development: 8 hours
- Stage 4 Quality Review: 1 hour

Output Files:
- Product Spec: docs/product/product-spec-20240308.md
- Technical Design: docs/technical/technical-design-20240308.md
- Code Implementation: src/...
- Review Report: docs/review/review-report-20240308.md
```

## Notes

1. **Atomic Execution**: Each stage focuses on completing current task, no skipping
2. **Review Driven**: Proceed based on review results, cannot skip reviews
3. **Detailed Logging**: Log each action for traceability
4. **Exception Reporting**: Report issues promptly when unable to resolve
5. **Documentation First**: Output docs before continuing to next step
