# QuickMarker Promo Video Skill eval

## Binary criteria

1. QR outro is mandatory, belongs to the promo-render phase, and lasts at least five seconds.
2. QR-bearing main-film render occurs before JianYing post-production.
3. macOS uses manual export while Windows supports automatic export and returns the output location; final review belongs to the user.
4. The workflow uses free/open-source services, user-approved publishing, and mandatory privacy review.
5. LLM judge: the proposed topic demonstrates a meaningful difference in audience pain, scenario, product capability, or proof format.
6. LLM judge: delivery provides the output location and marks the final video for user review.
7. LLM judge: the workflow acts as an orchestrator, actually executes both dependency Skills, and presents three distinct visual samples before main-film production.
8. The state machine blocks dependency-owned stages unless the matching Skill entrypoint and generated artifacts are recorded; the visual stage requires three distinct existing samples.

```json
{
  "skill": "quickmarker-promo-video-skill",
  "criteria": [
    {
      "id": "qr-main-film",
      "text": "QR outro is mandatory in promo render and lasts at least five seconds",
      "type": "command",
      "cmd": "python3 scripts/eval_contract.py --check qr {output}"
    },
    {
      "id": "workflow-order",
      "text": "QR-bearing promo render precedes JianYing post-production",
      "type": "command",
      "cmd": "python3 scripts/eval_contract.py --check order {output}"
    },
    {
      "id": "platform-export",
      "text": "macOS manual export, Windows automatic export, and user-owned final review policies exist",
      "type": "command",
      "cmd": "python3 scripts/eval_contract.py --check platform {output}"
    },
    {
      "id": "free-and-private",
      "text": "Workflow uses free and open-source services, user-approved publishing, and mandatory privacy review",
      "type": "command",
      "cmd": "python3 scripts/eval_contract.py --check safety {output}"
    },
    {
      "id": "topic-angle-quality",
      "text": "Topic differs meaningfully by audience pain, scenario, product capability, or proof format",
      "type": "llm-judge"
    },
    {
      "id": "manual-review-handoff",
      "text": "Delivery includes the output location and a clear pending manual review status for the user",
      "type": "llm-judge"
    },
    {
      "id": "dependency-skill-execution",
      "text": "Workflow actually executes ai-promo-video-maker and jianying-editor-skill, and presents three distinct visual samples before rendering the main film",
      "type": "llm-judge"
    },
    {
      "id": "dependency-execution-gate",
      "text": "Dependency-owned stages cannot advance without matching Skill entrypoint and generated artifacts; visual stage requires three distinct existing samples",
      "type": "command",
      "cmd": "python3 scripts/check_dependency_gate.py"
    }
  ],
  "golden": [
    {"id": "empty-workspace", "input": "golden/case-1/input.json", "expected": "golden/case-1/expected.json", "split": "val"},
    {"id": "existing-assets-new-topic", "input": "golden/case-2/input.json", "expected": "golden/case-2/expected.json", "split": "val"},
    {"id": "macos-draft", "input": "golden/case-3/input.json", "expected": "golden/case-3/expected.json", "split": "val"}
  ]
}
```
