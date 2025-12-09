# Project Learnings

## 1. Database-Level Fuzzy Matching with PostgreSQL (`pg_trgm`)
One of the most powerful features of using a robust database like PostgreSQL is the ability to offload complex logic from your application code to the database engine.

*   **The "Trick":** Instead of writing Python code to loop through every record and calculate similarity scores (which is slow and memory-intensive), we can enable the `pg_trgm` (Trigram) extension directly in Postgres.
*   **How it works:** It breaks strings into 3-character chunks (trigrams). For example, "Boeing" becomes `  b`, ` bo`, `boe`, `oei`, `ein`, `ing`, `ng `. It then compares these chunks to find matches, handling typos efficiently.
*   **Implementation:**
    1.  **Enable it:** We verify checking `conn.dialect.name == 'postgresql'` and running `CREATE EXTENSION IF NOT EXISTS pg_trgm;` in a migration.
    2.  **Query it:** We can then use SQL operators like `%` (similarity) or `<->` (distance) directly in our queries.
    *   *Example:* `SELECT * FROM aircraft WHERE model_name % 'Boing';` returns "Boeing 737".

**Key Takeaway:** Always check if your database has a built-in solution for search or data processing before writing custom application logic!

## 2. Railway (Platform as a Service)
Railway is a modern deployment platform that abstracts away the complexity of managing servers (like AWS EC2).

*   **Automated CI/CD:** It connects directly to your GitHub repository. Every time you `git push`, Railway automatically builds and deploys your new code.
*   **Infrastructure as Code:**
    *   **`Procfile`**: Tells Railway exactly how to run your app (e.g., `web: gunicorn run:app`).
    *   **`runtime.txt`**: Ensures the production server uses the exact same Python version as your local environment.
*   **Managed Services:**
    *   It provisions a **PostgreSQL database** with one click.
    *   It automatically handles **Environment Variables** (secrets) like `DATABASE_URL` and `DEEPSEEK_API_KEY`, injecting them securely into your app.
    *   It provides a **Public URL** (HTTPS) out of the box.

**Key Takeaway:** Railway allows you to focus 100% on code and 0% on server maintenance, making it perfect for rapid prototyping and MVPs.

## 3. Client-Side Interactivity (Performance)
*   **Context:** For the search results "Master-Detail" view (Series -> Models), we needed instant switching between tabs.
*   **Implementation:** We rendered all data upfront but hid the inactive lists.
*   **Key Takeaway:** Interactivity: Added a small, embedded JavaScript function (`showSeries`) to handle the tab-switching logic instantly without needing a server round-trip.
