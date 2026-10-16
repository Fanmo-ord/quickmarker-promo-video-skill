# QuickMarker Promo Video Skill eval

## Binary criteria

1. QR outro is mandatory, belongs to the promo-render phase, and lasts at least five seconds.
2. QR-bearing main-film render occurs before JianYing post-production.
3. macOS uses manual export while Windows supports validated automatic export.
4. The workflow uses free/open-source services, user-approved publishing, and mandatory privacy review.
5. LLM judge: the proposed topic demonstrates a meaningful difference in audience pain, scenario, product capability, or proof format.
6. LLM judge: final video keeps a full-size main canvas, one bottom subtitle layer, intelligible narration, readable cover, and scannable QR outro.

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
      "text": "macOS manual and Windows validated automatic export policies exist",
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
      "id": "final-media-quality",
      "text": "Final media has full-size picture, bottom subtitles, clear mix, readable cover, and scannable QR",
      "type": "llm-judge"
    }
  ],
  "golden": [
    {"id": "empty-workspace", "input": "golden/case-1/input.json", "expected": "golden/case-1/expected.json", "split": "val"},
    {"id": "existing-assets-new-topic", "input": "golden/case-2/input.json", "expected": "golden/case-2/expected.json", "split": "val"},
    {"id": "macos-draft", "input": "golden/case-3/input.json", "expected": "golden/case-3/expected.json", "split": "val"}
  ]
}
```
