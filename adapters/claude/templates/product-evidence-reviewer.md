---
name: product-evidence-reviewer
description: "실제 원문과 상품기획 후보의 모델 귀속·주장·조건·반례를 독립 대조할 필요가 있을 때만 사용한다."
tools: Read, Glob, Grep
disallowedTools: Bash, Write, Edit, Agent, Task, Skill, WebFetch, WebSearch, mcp__*
model: inherit
permissionMode: default
maxTurns: 6
---

{{instructions}}
