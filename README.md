# EU AI Act & GDPR Assistant (RAG)

Ask a question about the EU AI Act or the GDPR in German or English. The answer shows which article it came from.

> Not legal advice.

## Setup (Windows, PowerShell)

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## Folders

| Folder | What is inside |
|---|---|
| `data/raw` | Law texts downloaded from EUR-Lex |
| `data/processed` | Laws split into articles and recitals |
| `src` | Project code |
| `tests` | Tests |
| `notebooks` | Experiments |

## Status

- [x] Step 0: Setup
- [x] Step 1: Download and split the laws (1,170 pieces: recitals, articles, annexes in EN + DE)
- [ ] Step 2: Chunking + embeddings
