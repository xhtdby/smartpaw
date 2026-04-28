# Test Fixture Categories

The fixture tree is split by what the tests are allowed to prove.

- `router/labels.json`: text-only routing and card fixtures. These do not use image URLs and can run without Groq or network access.
- `mock_vision/labels.json`: mocked vision payloads for response/schema normalization. These prove API shape and contract behavior, not visual diagnosis.
- `verified_images/labels.json`: local image fixtures whose visible content is known and can be used as visual truth. This suite is intentionally empty until reviewed local images are added.
- `quarantined_external_*`: old external URL labels. These are kept only as historical prompts and must not be used as visual truth for bleeding, fracture, choking, seizure, heatstroke, eye injury, or other medical labels.

Do not add a URL-backed image fixture unless the image content is reviewed and the test expectation only claims what is actually visible.
