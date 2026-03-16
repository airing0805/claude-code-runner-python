# Multi-Agent Collaboration System

> Multi-role workflow system based on Claude Code Runner

## System Overview

This system defines the complete process for multiple roles (Director, PM, Tech Manager, Architect, Developer) to collaborate on tasks.

## Role System

| Role | Skill | Core Responsibility |
|------|-------|---------------------|
| **Director** | `/director-product-management` | Strategic planning, task assignment, output review |
| **Product Manager** | `/senior-product-manager` | Requirements analysis, product design |
| **Senior Architect** | `/senior-architect` | Technical review, architecture design |
| **Tech Manager** | `/tech-manager` | Technical planning, code implementation & fixes |
| **Senior Fullstack** | `/senior-fullstack` | Code quality review, feature completeness |

## Workflow Types

### 1. Feature Workflow

For new feature development:
```
Product Planning → Technical Design → Development → Quality Review → Complete
```

### 2. Bugfix Workflow

For issue fixes:
```
Technical Assessment → Fix Execution → Testing → Review → Complete
```

### 3. Optimization Workflow

For performance optimization, refactoring, etc:
```
Technical Review → Implementation → Verification → Complete
```

## Quick Start

### Method 1: Task Manager (Recommended)

```
/task-manager

Task: Design an AI assistant admin panel
Type: feature
Priority: P1
```

The system will automatically coordinate roles to complete the task.

### Method 2: Direct Role Invocation

```
# 1. Director initiates
/director-product-management

Task: Plan AI assistant admin panel features

# 2. Product planning
/senior-product-manager

Strategic Direction: [from Director]
Task Description: [specific requirements]

# 3. Technical design
/tech-manager

Task: Create technical design based on requirements

# 4. Architecture review
/senior-architect review

Design Doc: docs/technical/xxx.md

# 5. Development execution
/tech-manager stage 2: code implementation

Task: Implement admin panel
```

## Workflow Details

### Stage 1: Product Planning

| Step | Executor | Output |
|------|----------|--------|
| Strategic Analysis | Director | Strategic direction |
| Requirements Analysis | Senior PM | Product spec / requirements |
| Review | Director | Review result |

### Stage 2: Technical Design

| Step | Executor | Output |
|------|----------|--------|
| Design | Tech Manager | Technical design doc |
| Review | Senior Architect | Review report |

### Stage 3: Development

| Step | Executor | Output |
|------|----------|--------|
| Task Breakdown | Tech Manager | Task list |
| Code Implementation | Tech Manager | Code implementation |
| Acceptance | Tech Manager | Acceptance result |

### Stage 4: Quality Review

| Step | Executor | Output |
|------|----------|--------|
| Code Review | Senior Architect | Architecture review |
| Quality Review | Senior Fullstack | Quality review |
| Feature Acceptance | Senior PM | Feature acceptance |
| Final Review | Director | Final decision |

## Document Structure

```
.claude/
├── workflows/              # Workflow definitions
│   ├── task-workflow.md    # Task flow rules
│   ├── execution-flow.md   # Execution flow
│   └── tasks/
│       └── task-manager.md # Task manager
└── skills/                 # Agent Skills
    ├── director-product-management/
    ├── senior-product-manager/
    ├── tech-manager/
    ├── senior-architect/
    └── senior-fullstack/
```

## Review Decisions

### Product Spec Review

| Result | Condition |
|--------|-----------|
| ✅ Approved | Clear requirements, complete solution, clear value |
| 🔄 Needs Revision | Unclear requirements or incomplete solution |
| ❌ Rejected | Direction deviates or insufficient value |

### Technical Design Review

| Result | Condition |
|--------|-----------|
| ✅ Approved | Reasonable design, feasible tech, controllable risk |
| 🔄 Needs Revision | Design flaws or technical challenges |
| ❌ Rejected | Not feasible or too risky |

### Final Quality Review

| Result | Condition |
|--------|-----------|
| ✅ Ship | All reviews passed |
| 🔄 Defer | Outstanding issues |
| ❌ Rollback | Serious issues |

## Execution Example

### Complete Example

```
User: /task-manager

Task: Implement user login feature
Type: feature
Priority: P0

---

System: ✅ Task created TASK-20240308-001

Stage 1: Product Planning
System: Invoking /director-product-management for strategic analysis

Director: [strategic direction output]

System: Invoking /senior-product-manager for requirements analysis

Senior PM: [product solution output]

System: Invoking /director-product-management for review

Director: ✅ Approved

Stage 2: Technical Design
System: Invoking /tech-manager for technical design

Tech Manager: [technical design output]

System: Invoking /senior-architect for review

Senior Architect: ✅ Approved

Stage 3: Development
System: Invoking /tech-manager for task breakdown

Tech Manager: [task list]
System: Executing code implementation...

Stage 4: Quality Review
System: Invoking /senior-architect for code review
System: Invoking /senior-fullstack for quality review
System: Invoking /senior-product-manager for feature acceptance

Director: ✅ Final approval - Ship

System: ✅ Task complete!
```

## Best Practices

1. **Atomic Execution**: Each role focuses on current task, no skipping
2. **Review Driven**: All outputs must be reviewed before proceeding
3. **Documentation First**: Output docs before continuing
4. **Detailed Logging**: Log each stage for traceability
5. **Exception Handling**: Report issues promptly

## Extension

To add new roles or modify workflows:
- `.claude/workflows/task-workflow.md` - Flow rules
- `.claude/workflows/execution-flow.md` - Execution flow
