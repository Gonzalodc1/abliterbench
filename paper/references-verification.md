# Reference verification log

Each entry in `references.bib` was checked against an authoritative source (arXiv abstract page,
OpenReview, the proceedings/publisher page, DBLP, or Project Euclid). Pointers below are so a
reader or endorser can confirm venue + year by hand. Status as of 2026-06-17. **19/19 confirmed;
no venue/year corrections.**

| key | arXiv / DOI | venue, year | confirmed via |
|---|---|---|---|
| arditi2024refusal | arXiv:2406.11717 | NeurIPS 2024 | DBLP `conf/nips/ArditiOSPPGN24`; NeurIPS virtual poster 93566 |
| wei2024brittleness | arXiv:2402.05162 | ICML 2024, PMLR v235:52588–52610 | OpenReview `K6xxnKN2gm`; proceedings.mlr.press/v235/wei24f.html |
| qi2024finetuning | arXiv:2310.03693 | ICLR 2024 (Oral) | OpenReview `hTEGyKf0dZ`; iclr.cc/virtual/2024/oral/19735 |
| krupkina2024badgpt4o | arXiv:2412.05346 | preprint (2024) | arXiv abstract page; no venue comment |
| zhang2024cybench | arXiv:2408.08926 | ICLR 2025 (Oral) | arXiv comments field: "ICLR 2025 Oral" |
| shao2024nyuctf | arXiv:2406.05590 | NeurIPS 2024 D&B, pp 57472–57498 | OpenReview `itBDglVylS`; NeurIPS D&B proceedings |
| gioacchini2024autopenbench | arXiv:2410.03225 | preprint (2024) | arXiv abstract page; no venue comment |
| abramovich2025enigma | arXiv:2409.16165 | ICML 2025 | arXiv comments field: "ICML 2025" |
| yang2023intercode | arXiv:2306.14898 | NeurIPS 2023 D&B | NeurIPS 2023 D&B proceedings |
| deng2024pentestgpt | arXiv:2308.06782 | 33rd USENIX Security 2024, pp 847–864 | usenix.org/conference/usenixsecurity24/presentation/deng; ISBN 978-1-939133-44-1 |
| bhatt2023cyberseceval | arXiv:2312.04724 | preprint (2023) | arXiv abstract page; no venue comment |
| bhatt2024cyberseceval2 | arXiv:2404.13161 | preprint (2024) | arXiv abstract page; no venue comment |
| wan2024cyberseceval3 | arXiv:2408.01605 | preprint (2024) | arXiv abstract page; no venue comment |
| inan2023llamaguard | arXiv:2312.06674 | preprint (2023) | arXiv abstract page; no venue comment |
| staab2024beyond | arXiv:2310.07298 | ICLR 2024 | OpenReview `kmn0BhQk7p`; ICLR 2024 poster 17964 |
| shafee2025osint | arXiv:2401.15127 | Expert Systems w/ Applications 261:125509 (2025) | arXiv journal-ref; ScienceDirect article 125509 |
| efron1979bootstrap | DOI 10.1214/aos/1176344552 | Annals of Statistics 7(1):1–26, 1979 | Project Euclid |
| diciccio1996bootstrap | DOI 10.1214/ss/1032280214 | Statistical Science 11(3):189–228, 1996 | Project Euclid |
| efron1993introduction | ISBN 978-0412042317 | Chapman & Hall/CRC, 1993 | publisher / WorldCat |

Notes: PentestGPT's arXiv title differs from the USENIX-published title; the `.bib` uses the
USENIX title. `efron1993introduction` lists both Efron and Tibshirani. Qi 2024 and Cybench are both
Orals (not reflected in the entries, cosmetic).
