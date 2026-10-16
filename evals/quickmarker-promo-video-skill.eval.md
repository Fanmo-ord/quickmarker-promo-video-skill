# QuickMarker Promo Video Skill eval

## Binary criteria

1. The QR outro is mandatory, belongs to the promo-render phase, and lasts at least five seconds.
2. The QR-bearing main-film render occurs before JianYing post-production.
3. macOS requires manual export while Windows allows validated automatic export.
4. Paid services and automatic publishing are disabled, and privacy review is mandatory.
5. LLM judge: the proposed topic uses a meaningfully different audience pain, scenario, product capability, or proof format—not merely a renamed old title.
6. LLM judge: the final video keeps a full-size main canvas, one bottom subtitle layer, intelligible narration, readable cover, and scannable QR outro.

```json
{"skill":"quickmarker-promo-video-skill","criteria":[{"id":"qr-main-film","text":"QR outro is mandatory in promo render and lasts at least five seconds","type":"command","cmd":"python3 scripts/eval_contract.py --check qr {output}"},{"id":"workflow-order","text":"QR-bearing promo render precedes JianYing post-production","type":"command","cmd":"python3 scripts/eval_contract.py --check order {output}"},{"id":"platform-export","text":"macOS manual and Windows validated automatic export policies exist","type":"command","cmd":"python3 scripts/eval_contract.py --check platform {output}"},{"id":"free-and-private","text":"No paid service or auto publishing; privacy review is mandatory","type":"command","cmd":"python3 scripts/eval_contract.py --check safety {output}"},{"id":"topic-angle-quality","text":"Repeated topics are rejected by angle, not only title","type":"llm-judge"},{"id":"final-media-quality","text":"Final media has full-size picture, bottom subtitles, clear mix, readable cover and scannable QR","type":"llm-judge"}],"golden":[{"id":"empty-workspace","input":"golden/case-1/input.json","expected":"golden/case-1/expected.json","split":"val"},{"id":"existing-assets-new-topic","input":"golden/case-2/input.json","expected":"golden/case-2/expected.json","split":"val"},{"id":"macos-draft","input":"golden/case-3/input.json","expected":"golden/case-3/expected.json","split":"val"}]}
```

