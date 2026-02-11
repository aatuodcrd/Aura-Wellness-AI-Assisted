# AI Prompts Documentation

## 1. System Prompt

**Used in:** `src/backend/app/api/v1/endpoints/rag.py`

```text
You are an intelligent internal knowledge assistant.

INSTRUCTIONS:
1. Answer the user's question based EXCLUSIVELY on the provided context below.
2. The context contains up to {top_k} most relevant document chunks. Synthesize information from them to answer accurately.
3. Do not use outside knowledge or make up information.
4. If the answer cannot be found in the context, state clearly that you do not know.
5. You MUST cite the source of your information for every claim, using the format [Source Title].

CONTEXT:
{context}

USER QUESTION:
{question}
```

## 2. Prompt Design & Iterations

The prompt evolved through 3 key iterations to address specific failures observed during testing.

### Iteration v1: The "Helpful Assistant" (Rejected)
*   **Prompt:** "You are a helpful assistant. Answer the user's question using the context provided."
*   **Outcome:** ❌ Failed on "Negative/Missing" queries.
*   **Failure Case:** When asked "How do I bake a cake?" (irrelevant query), the model used its internal training data to provide a recipe, which violates the "Internal Knowledge Only" rule.
*   **Fix:** Added strict constraints ("EXCLUSIVELY on provided context", "Do not use outside knowledge").

### Iteration v2: The "Silent Robot" (Rejected)
*   **Prompt:** "Answer based on context only. If not found, say 'I don't know'."
*   **Outcome:** ❌ Good refusal, but poor synthesis.
*   **Failure Case:** When valid information was spread across 2 chunks (e.g., Policy in Chunk A, Stipend Amount in Chunk B), the model often answered partially or failed to connect the dots because it treated chunks in isolation.
*   **Fix:** Added instruction to "Synthesize information" and explicitly mentioned `top_k` chunks to give the model permission to combine facts.

### Iteration v3: The "Cited Professional" (Accepted)
*   **Prompt:** Added "You MUST cite the source... [Source Title]".
*   **Outcome:** ✅ Success.
*   **Winning Factor:** This verified that the model wasn't hallucinating. If it couldn't find a source title in the context metadata, it naturally defaulted to "I don't know" more often, reducing false positives.

## 3. Why Human Judgment Was Required

Automated metrics (like BLEU/ROUGE) were insufficient for this system because:
1.  **Accuracy vs. Hallucination:** A high similarity score could still be factually wrong if the model "filled in the blanks" with outside knowledge. Human review was needed to verify that the *source* of the answer was strictly the provided text.
2.  **Tone & Formatting:** We needed the answer to be professional and structured. Only a human reviewer could assess if the "Citation Format" `[Source Title]` was being applied consistently across different document types (PDFs vs. Slack logs).
3.  **Refusal Logic:** Tuning the "I don't know" threshold is subjective. We needed humans to decide if a "Partial Answer" was better or worse than a "Refusal". We decided strict refusal was safer for Policy documents.

---

## 4. Accepted vs Rejected Outputs (Examples)

### Accepted Output
**Input Context:** "Acme allows remote work 2 days a week."  
**User Question:** "How many WFH days are allowed?"

```json
{
  "answer": "Acme allows remote work 2 days a week. [WFH Policy]",
  "sources": ["WFH Policy"]
}
```

**Why accepted:** Answer is fully grounded in provided context and cites the correct source.

### Rejected Output
**Input Context:** "Acme allows remote work 2 days a week."  
**User Question:** "What is Acme's parental leave policy?"

```json
{
  "answer": "Acme offers 12 weeks of paid parental leave. [HR Handbook]",
  "sources": ["HR Handbook"]
}
```

**Why rejected:** The answer fabricates policy content and cites a source that is not present in context. This violates the "context‑only" requirement.

---

## 5. Real Run Output (From e2e.sh)

### Upload Document Response
```json
{
  "title": "WFH Policy",
  "content": "Test tenant allows remote work 1 day a week.",
  "id": "850863cb-b72c-4e7d-9353-b340786dedb4",
  "project_id": "7f2e7932-d66e-462e-aa54-8b181b5fbe6a"
}
```

### Chat Response
```json
{
  "answer": "The policy allows for remote work 1 day a week [WFH Policy].",
  "sources": [
    {
      "title": "WFH Policy",
      "content": "Test tenant allows remote work 1 day a week...."
    }
  ]
}
```
