# Multi-Agent Collaboration Execution Flow

> Defines specific execution steps and Agent invocation methods for each stage

## Complete Task Execution Flow

### Stage 1: Product Planning

```
┌──────────────────────────────────────────────────────────────────┐
│  Step 1.1: Receive Task                                          │
│  - User invokes /director-product-management                    │
│  - Task description: Need to implement XXX feature              │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 1.2: Director Strategic Analysis                           │
│  Invoke: /director-product-management                            │
│  Input: Task description                                         │
│  Output: Strategic direction, target users, core value          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 1.3: PM Requirements Analysis                             │
│  Invoke: /senior-product-manager                                 │
│  Input: Strategic direction + Task description                  │
│  Output: Product spec / Requirements document                   │
│  Principle: Atomic tasks, one feature module at a time          │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 1.4: Director Review                                      │
│  Invoke: /director-product-management                           │
│  Input: Product spec                                             │
│  Review Dimensions: Clarity, completeness, business value        │
│  Output: Review result (Approved/Needs Revision/Rejected)      │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────────────────────────────────┐
                    │  If Approved                                │
                    │  Output: Requirements → Proceed to Stage 2  │
                    └──────────────────────────────────────────────┘
```

### Stage 2: Technical Design

```
┌──────────────────────────────────────────────────────────────────┐
│  Step 2.1: Tech Manager Design                                  │
│  Invoke: /tech-manager                                           │
│  Input: Requirements document                                    │
│  Output: Technical design document                               │
│  Execution:                                                       │
│  - Analyze requirements                                          │
│  - Review existing architecture                                  │
│  - Design technical implementation                              │
│  - Define API interfaces and data models                        │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 2.2: Senior Architect Review                               │
│  Invoke: /senior-architect                                        │
│  Input: Technical design + Requirements                         │
│  Review Dimensions:                                              │
│  - Completeness: All requirements covered                        │
│  - Consistency: Design matches requirements                      │
│  - Feasibility: Technical solution viable                       │
│  - Standards: Follows project standards                         │
│  - Extensibility: System supports extension                     │
│  Output: Review report                                           │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────────────────────────────────┐
                    │  Review Result: Approved                   │
                    │  Output: Technical Design → Stage 3        │
                    └──────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────────────────────────────────┐
                    │  Review Result: Needs Revision              │
                    │  Return to Step 2.1, Tech Manager revises   │
                    └──────────────────────────────────────────────┘
```

### Stage 3: Development

```
┌──────────────────────────────────────────────────────────────────┐
│  Step 3.1: Tech Manager Task Breakdown                          │
│  Invoke: /tech-manager                                           │
│  Input: Technical design document                                │
│  Output: Task breakdown (sub-task list)                         │
│  Principles:                                                      │
│  - Each sub-task can be completed independently                  │
│  - Sub-tasks have clear acceptance criteria                      │
│  - Identify task dependencies                                    │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 3.2: Development Execution (Loop for each sub-task)     │
│  Invoke: /tech-manager stage 2: code implementation             │
│  Input: Sub-task description + Technical design                 │
│  Execution:                                                       │
│  - Implement code per design                                     │
│  - Follow project coding standards                               │
│  - Write necessary test cases                                    │
│  - Update related documentation                                  │
│  Output: Code implementation + Execution log                     │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 3.3: Tech Manager Acceptance                              │
│  Invoke: /tech-manager                                           │
│  Input: Code implementation + Acceptance criteria                │
│  Acceptance:                                                     │
│  - Code matches design                                            │
│  - Follows coding standards                                       │
│  - Features complete                                             │
│  - Test cases exist                                              │
│  Output: Acceptance result                                       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────────────────────────────────┐
                    │  Acceptance Passed                          │
                    │  Output: All sub-tasks complete → Stage 4  │
                    └──────────────────────────────────────────────┘
```

### Stage 4: Quality Review

```
┌──────────────────────────────────────────────────────────────────┐
│  Step 4.1: Senior Architect Code Review                         │
│  Invoke: /senior-architect                                        │
│  Input: Code implementation + Technical design                  │
│  Review:                                                          │
│  - Architecture design reasonableness                            │
│  - Technical choices appropriateness                              │
│  - Performance considerations                                     │
│  - Security checks                                               │
│  Output: Architecture review report                               │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 4.2: Senior Fullstack Quality Review                      │
│  Invoke: /senior-fullstack                                       │
│  Input: Code implementation                                      │
│  Review:                                                          │
│  - Code quality                                                  │
│  - Feature completeness                                          │
│  - Test coverage                                                 │
│  Output: Quality review report                                   │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 4.3: PM Feature Acceptance                                │
│  Invoke: /senior-product-manager                                 │
│  Input: Requirements + Code implementation                       │
│  Acceptance:                                                     │
│  - Features match requirements                                   │
│  - User experience reasonable                                    │
│  - Boundary condition handling                                    │
│  Output: Feature acceptance report                               │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 4.4: Director Final Review                                │
│  Invoke: /director-product-management                           │
│  Input: All review reports                                       │
│  Review:                                                          │
│  - Comprehensive evaluation of all reviews                        │
│  - Make final decision                                           │
│  Output: Final decision (Ship/Defer/Rollback)                    │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌──────────────────────────────────────────────┐
                    │  Final Decision: Ship                       │
                    │  Task complete, output final execution report│
                    └──────────────────────────────────────────────┘
```

## Agent Invocation Templates

### Initiate Task (User → Director)

```
/director-product-management

Task: Design [product type] for [target users], solving [core pain point]

Background: [optional project background]
```

### Director Assigns Task (Director → PM)

```
/senior-product-manager

Strategic Direction: [Director's strategic direction]
Task Description: [specific task description]

Please analyze and output product spec.
```

### Technical Design (Tech Manager → Architect)

```
/senior-architect review

Design Doc: [technical design doc path]
Requirements Doc: [requirements doc path]

Please conduct technical review.
```

### Development Execution (Tech Manager)

```
/tech-manager stage 2: code implementation

Task: [specific task description]
Design Doc: [design doc path]
Acceptance Criteria: [acceptance criteria]

Please execute code implementation.
```

### Quality Review (Multi-role)

```
/senior-architect review

Review Scope: Code Implementation
Doc Paths: [code/design/requirements doc paths]
```

## Execution Log Template

When a role completes work, output execution log:

```markdown
# [Role] Execution Log

## Execution Info
- Executor: [role name]
- Start Time: [time]
- End Time: [time]
- Duration: [duration]

## Input
- Task Description: [description]
- Upstream Output: [doc path]

## Execution Content
### Main Work
1. [work 1]
2. [work 2]

### Output
- [output 1]: [path]
- [output 2]: [path]

## Review Comments (if any)
- Reviewer: [role]
- Review Result: [Approved/Needs Revision/Rejected]
- Comments: [specific comments]

## Next Step
- Next Role: [role]
- Next Task: [task description]
```
