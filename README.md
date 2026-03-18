# vision-paper-genealogy

Interactive genealogy tree visualizer for Computer Vision research methods.

論文の手法がどこから派生し、どう分岐したかをインタラクティブな系譜図で表示します。

## Concept

```
NeRF [2020] ★9,800
├── (↑ extends) Instant-NGP [2022] ★16,000
├── (↑ extends) Mip-NeRF [2021] ★1,100
│   └── (↑ extends) Mip-NeRF 360 [2022] ★1,500
│       └── (+ combines) Zip-NeRF [2023] ★700
├── (⇨ replaces) Plenoxels [2022] ★2,800
├── (↑ extends) DreamFusion [2022] ★8,200
└── (⇨ replaces) 3D Gaussian Splatting [2023] ★20,000
    ├── (↑ extends) SuGaR [2024] ★2,200
    ├── (↑ extends) 2D Gaussian Splatting [2024] ★2,000
    └── (↑ extends) DreamGaussian [2023] ★4,200
```

## Install

```bash
pip install -e .
```

## Usage

```bash
# Show genealogy tree for all domains
vision-paper-genealogy show

# Show a specific domain
vision-paper-genealogy show neural_radiance_fields

# Trace ancestors of a method
vision-paper-genealogy ancestors "3D Gaussian Splatting"

# Show detailed info about a method
vision-paper-genealogy info "LoFTR"

# List all methods (filter by tag or year)
vision-paper-genealogy list --tag transformer
vision-paper-genealogy list --year 2024
```

## Relation Types

| Symbol | Type | Meaning |
|--------|------|---------|
| ↑ | `extends` | Direct extension of the parent method |
| + | `combines` | Combines ideas from multiple methods |
| ⇨ | `replaces` | Paradigm shift — replaces the parent approach |
| ✱ | `inspires` | Indirect influence, not a direct derivative |

## Adding a Domain

Create a YAML file in `domains/`:

```yaml
name: Your Domain Name
description: Brief description
source_awesome_lists:
  - https://github.com/...

methods:
  - name: "MethodName"
    paper: "Full Paper Title"
    arxiv: "XXXX.XXXXX"
    year: 2024
    code: "github-user/repo"
    stars: 1000
    tags: [tag1, tag2]
    parents:
      - name: "ParentMethod"
        relation: extends  # extends | combines | replaces | inspires
    description: "One-line description"
```

## Domains

Currently included:

- **Neural Radiance Fields & 3D Gaussian Splatting** — NeRF → 3DGS evolution
- **Image Matching & Feature Detection** — SIFT → SuperPoint → LoFTR → DUSt3R evolution

## License

MIT
