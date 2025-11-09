# 🔍 Debug Logging for Vector Store Usage

## Issue Identified

**Problem**: When clicking "Start Agent Analysis", the vector store may not be used even if it exists.

**Root Cause**: The `retrieve_evidence()` function is called **without passing the session manager or vector store directory**, so it defaults to looking at `data/vector_store/` instead of the session-specific path like `data/sessions/<session-id>/vector_store/`.

---

## Debug Logging Added

I've added comprehensive debug logging at three key points:

### 1. **ResearchWorkflow.run()** (Entry Point)
Location: `src/agents/research_graph.py`

**Logs:**
```
DEBUG: ResearchWorkflow.run() called
DEBUG: Query: [your query]
DEBUG: Number of papers: [count]
DEBUG: Sample paper keys: [list of keys]
DEBUG: Papers with pdf_path: [count]
DEBUG: Sample pdf_path: [path]
```

**What to check:**
- Are papers being passed?
- Do papers have `pdf_path` field?
- Where are the PDFs located?

---

### 2. **ResearchAgent.process()** (First Agent)
Location: `src/agents/agent_definitions.py`

**Logs:**
```
DEBUG: ResearchAgent.process() called
DEBUG: Query: [query]
DEBUG: Number of papers: [count]
DEBUG: Papers have pdf_path: [True/False]
DEBUG: Attempting to retrieve evidence from vector store...
```

**What to check:**
- Is the ResearchAgent receiving the papers?
- Do papers have pdf_path?

---

### 3. **retrieve_evidence()** (Vector Store Query)
Location: `src/agents/agent_definitions.py`

**Detailed Logs:**
```
DEBUG: retrieve_evidence() called
DEBUG:   query: [query]
DEBUG:   k: [number]
DEBUG:   vector_store_dir: [None/path]
DEBUG:   session_manager: [None/SessionManager]
DEBUG:   Using default path: data/vector_store
DEBUG:   Checking path: [path]
DEBUG:   Path exists: [True/False]
DEBUG:   Contents: [list of files]
DEBUG:   Vector store exists: [True/False]
```

**If vector store NOT found:**
```
DEBUG:   ❌ Vector store does not exist at this path
DEBUG:   Looking for:
DEBUG:     - [path]/index.faiss
DEBUG:     - [path]/chunks.json
DEBUG:     - [path]/metadata.json
```

**If vector store found:**
```
DEBUG:   ✅ Vector store found, querying...
DEBUG:   Query returned [count] results
```

**Final result in ResearchAgent:**
```
DEBUG: ✅ Successfully retrieved [count] chunks from vector store
DEBUG: Sample chunk score: 0.823
DEBUG: Sample chunk preview: [text]...
```

OR

```
DEBUG: ❌ No evidence retrieved from vector store - will use abstracts
```

---

## How to Test

### Using Streamlit UI

1. **Start the app:**
   ```bash
   streamlit run app.py
   ```

2. **Create or load a session** with papers and vector store built

3. **Click "Start Agent Analysis"**

4. **Watch the terminal** for debug logs

5. **Look for these specific logs:**
   - `DEBUG: Using default path: data/vector_store` ← **This is the problem!**
   - `DEBUG: Path exists: False` ← Vector store not at default location
   - Should be: `DEBUG: Using session_manager path: data/sessions/[session-id]/vector_store`

---

### Using CLI

1. **Run research command:**
   ```bash
   python cli.py research "quantum computing" --session-id <your-session-id> --verbose
   ```

2. **Watch for debug logs** in the output

---

## Expected Debug Output

### If Working Correctly (with session):

```
================================================================================
DEBUG: ResearchWorkflow.run() called
DEBUG: Query: quantum computing applications
DEBUG: Number of papers: 10
DEBUG: Papers with pdf_path: 10
DEBUG: Sample pdf_path: data/sessions/quantum_computing_a1b2/papers/paper1.pdf
================================================================================
DEBUG: ResearchAgent.process() called
DEBUG: Query: quantum computing applications
DEBUG: Papers have pdf_path: True
DEBUG: Attempting to retrieve evidence from vector store...
DEBUG: retrieve_evidence() called
DEBUG:   vector_store_dir: None
DEBUG:   session_manager: None
DEBUG:   Using default path: data/vector_store  ⚠️ PROBLEM HERE!
DEBUG:   Path exists: False
DEBUG:   ❌ Vector store does not exist at this path
DEBUG: ❌ No evidence retrieved from vector store - will use abstracts
================================================================================
```

### What Should Happen (Fixed):

```
DEBUG: retrieve_evidence() called
DEBUG:   session_manager: <SessionManager>
DEBUG:   Using session_manager path: data/sessions/quantum_computing_a1b2/vector_store
DEBUG:   Path exists: True
DEBUG:   Contents: ['index.faiss', 'chunks.json', 'metadata.json']
DEBUG:   Vector store exists: True
DEBUG:   ✅ Vector store found, querying...
DEBUG:   Query returned 10 results
DEBUG: ✅ Successfully retrieved 10 chunks from vector store
```

---

## The Fix Needed

### Current Problem:
```python
# In ResearchAgent.process()
evidence_hits = retrieve_evidence(query, k=10)  # No session info!
```

### Solution Required:

We need to pass the session information through the workflow. There are several approaches:

#### Option 1: Add session_manager to AgentState
```python
class AgentState(TypedDict):
    query: str
    papers: List[Dict]
    session_manager: Optional[Any]  # Add this
    # ... other fields
```

#### Option 2: Extract vector_store path from papers
```python
# In ResearchAgent.process()
if papers and papers[0].get('pdf_path'):
    # Extract session path from pdf_path
    pdf_path = papers[0]['pdf_path']
    # data/sessions/[session-id]/papers/paper.pdf
    # Extract: data/sessions/[session-id]/vector_store
    import os
    session_dir = os.path.dirname(os.path.dirname(pdf_path))
    vector_store_dir = os.path.join(session_dir, 'vector_store')
    evidence_hits = retrieve_evidence(query, k=10, vector_store_dir=vector_store_dir)
```

#### Option 3: Store vector_store_dir in papers metadata
```python
# When loading papers in app.py or cli.py, add:
for paper in papers:
    paper['vector_store_dir'] = session_manager.get_vector_store_dir()

# Then in ResearchAgent:
if papers and papers[0].get('vector_store_dir'):
    evidence_hits = retrieve_evidence(query, k=10, vector_store_dir=papers[0]['vector_store_dir'])
```

---

## Quick Test Commands

### Test 1: Check if vector store exists
```python
from ingestion.document_processor import DocumentProcessor

# Check default location
dp = DocumentProcessor(vector_store_dir="data/vector_store")
print(f"Default location exists: {dp.store_exists()}")

# Check session location (replace with your session ID)
dp = DocumentProcessor(vector_store_dir="data/sessions/your_session_id/vector_store")
print(f"Session location exists: {dp.store_exists()}")
```

### Test 2: Manual retrieve_evidence test
```python
from agents.agent_definitions import retrieve_evidence

# Test with default (will likely fail)
result = retrieve_evidence("quantum computing", k=5)
print(f"Default path result: {result}")

# Test with session path
result = retrieve_evidence("quantum computing", k=5, 
                          vector_store_dir="data/sessions/your_session_id/vector_store")
print(f"Session path result: {len(result) if result else 0} chunks")
```

---

## Summary

**Current Behavior:**
- ❌ `retrieve_evidence()` looks in `data/vector_store/` (wrong path for sessions)
- ❌ Vector store not found at default path
- ❌ Falls back to using paper abstracts

**What the Debug Logs Will Show:**
- The exact path being checked
- Whether the path exists
- What files are in the directory
- Whether each required file exists
- The actual error if something fails

**Next Step:**
After running with debug logs, we'll see exactly where it's looking and implement the appropriate fix to pass the session path correctly.

---

## Running the Debug

1. **Start your app**: `streamlit run app.py`
2. **Load a session** with built vector store
3. **Click "Start Agent Analysis"**
4. **Copy the debug output** from terminal
5. **Look for the path** it's checking

The logs will definitively show if the issue is the path mismatch!

