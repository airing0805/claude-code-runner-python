# Multi-Agent Workflow Definition

> Defines the complete process for tasks to flow between roles

## Workflow Types

### 1. Feature Workflow

```
User Request → Product Planning → Technical Design → Development → Quality Review → Complete
```

### 2. Bugfix Workflow

```
Issue Report → Technical Assessment → Fix Execution → Testing → Review → Complete
```

### 3. Optimization Workflow

```
Optimization Proposal → Technical Review → Implementation → Verification → Complete
```

## Task Flow Rules

### Stage Transition

| Current Stage | Next Stage | Trigger Condition |
|---------------|------------|-------------------|
| Init | Product Planning | User submits task |
| Product Planning | Technical Design | Product spec approved |
| Technical Design | Development | Technical design approved |
| Development | Quality Review | Code implementation complete |
| Quality Review | Complete | All reviews approved |
| Any Stage | Rejected | Review not passed |

### Role Assignment Rules

```yaml
Stage1_ProductPlanning:
  Lead Role: Director
  Execute Role: Senior PM
  Review Role: Director
  Output: Product Spec / Requirements

Stage2_TechnicalDesign:
  Lead Role: Tech Manager
  Execute Role: Tech Manager
  Review Role: Senior Architect
  Output: Technical Design Document

Stage3_Development:
  Lead Role: Tech Manager
  Execute Role: Tech Manager / Developer
  Review Role: Tech Manager
  Output: Code Implementation

Stage4_QualityReview:
  Lead Role: Tech Manager
  Execute Role: Senior Architect / Senior Fullstack
  Review Role: Director
  Output: Review Report / Ship Approval
```

## Task State Definition

| State | Description | Transitable States |
|-------|-------------|-------------------|
| PENDING | Waiting to be processed | IN_PROGRESS |
| IN_PROGRESS | In progress | PENDING_REVIEW, BLOCKED |
| PENDING_REVIEW | Waiting for review | IN_PROGRESS, APPROVED, REJECTED |
| BLOCKED | Blocked | IN_PROGRESS |
| APPROVED | Approved | NEXT_PHASE |
| REJECTED | Rejected | IN_PROGRESS |
| NEXT_PHASE | Next phase | Depends on stage |
| COMPLETED | Completed | - |
| CANCELLED | Cancelled | - |

## Review Decision Matrix

### Product Spec Review

| Review Result | Condition | Next Action |
|---------------|-----------|-------------|
| Approved | Clear requirements, complete solution, clear value | Proceed to Technical Design |
| Needs Revision | Unclear requirements or incomplete solution | Return to Senior PM |
| Rejected | Direction deviates or insufficient value | Task terminated |

### Technical Design Review

| Review Result | Condition | Next Action |
|---------------|-----------|-------------|
| Approved | Reasonable design, feasible tech, controllable risk | Proceed to Development |
| Needs Revision | Design flaws or technical challenges | Return to Tech Manager |
| Rejected | Not feasible or too risky | Task terminated or re-requirements |

### Code Implementation Review

| Review Result | Condition | Next Action |
|---------------|-----------|-------------|
| Approved | Code quality met, feature complete | Proceed to Quality Review |
| Needs Revision | Code issues or incomplete features | Return to developer |
| Rejected | Serious design deviation | Redesign required |

### Final Quality Review

| Review Result | Condition | Next Action |
|---------------|-----------|-------------|
| Ship | All reviews passed | Task complete |
| Defer | Outstanding issues | Re-review after fixes |
| Rollback | Serious issues | Return to development |

## Task Priority Rules

| Priority | Description | Weight |
|----------|-------------|--------|
| P0 - Critical | Must be processed immediately | 100 |
| P1 - High | Complete within this week | 80 |
| P2 - Medium | Complete within this month | 60 |
| P3 - Low | Complete within this quarter | 40 |

## Task Lifecycle

```
Create → Assign → Execute → Self-Check → Submit for Review → Review → Revise/Approve → Next Phase → ... → Complete
```

### Time Limits per Stage

| Stage | Suggested Duration | Max Duration |
|-------|-------------------|---------------|
| Product Planning | 2-4 hours | 24 hours |
| Technical Design | 2-4 hours | 24 hours |
| Development | Per task | Per task |
| Quality Review | 1-2 hours | 8 hours |
