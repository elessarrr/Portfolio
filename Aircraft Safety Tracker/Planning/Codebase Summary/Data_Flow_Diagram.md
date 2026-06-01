graph TD
    A[User] --> B[Frontend (HTMX/Jinja2)]
    B -- HTTP GET/POST --> C[Flask Backend]
    C -- SQLAlchemy Queries --> D[Database (PostgreSQL/SQLite)]
    D -- Query Results --> C
    C -- HTML Render --> B
    B -- Display --> A

    %% LLM Analysis Flow
    A -- Submit Report/Regenerate Summary --> B
    B -- HTMX POST --> C
    C -- Enqueue Job (generate_summary_background) --> E[RQ Queue (Redis)]
    E -- Pick Up Job --> F[RQ Worker]
    F -- API Call (DeepSeek) --> G[DeepSeek API]
    F -- API Call (Gemini) --> H[Gemini API]
    G -- LLM Response --> F
    H -- LLM Response --> F
    F -- Store Summary/Update Job Status --> D
    C -- Poll Job Status --> D
    D -- Job Status --> C
    C -- Update UI --> B

    %% Data Ingestion Flow
    Admin[Admin/CLI] --> L[Data Ingestion Module]
    L -- Fetch Raw Data --> I[NTSB API]
    L -- Fetch Raw Data --> J[FAA SDR API]
    L -- Fetch Raw Data --> K[FAA AIDS API]
    I -- Raw Data --> L
    J -- Raw Data --> L
    K -- Raw Data --> L
    L -- Transform Data (Parse, Canonicalize, Dedupe) --> M[Data Transformation]
    M -- Upsert Processed Data --> D