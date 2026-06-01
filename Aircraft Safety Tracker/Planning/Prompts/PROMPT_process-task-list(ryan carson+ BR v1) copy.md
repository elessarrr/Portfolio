# Task List Management

Guidelines for managing task lists in markdown files to track progress on completing a PRD

## Task Implementation

- **One sub-task at a time:** Do **NOT** start the next sub‑task until you ask the user for permission and they say "yes" or "y"
- **Completion protocol:**
  1. When you finish a **sub‑task**, immediately mark it as completed by changing `[ ]` to `[x]`.
  2. If **all** subtasks underneath a parent task are now `[x]`, follow this sequence:
  - **First**: Run the full test suite (`pytest`, `npm test`, `bin/rails test`, etc.)
  - **Only if all tests pass**: Stage changes (`git add .`)
  - **Clean up**: Remove any temporary files and temporary code before committing
  - **Commit**: Use a descriptive commit message that:
    - Uses conventional commit format (`feat:`, `fix:`, `refactor:`, etc.)
    - Summarizes what was accomplished in the parent task
    - Lists key changes and additions
    - References the task number and PRD context
    - **Formats the message as a single-line command using** **`-m`** **flags**, e.g.:
      ```
      git commit -m "feat: add payment validation logic" -m "- Validates card type and expiry" -m "- Adds unit tests for edge cases" -m "Related to T123 in PRD"
      ```
  1. Once all the subtasks are marked completed and changes have been committed, mark the **parent task** as completed.
- Stop after each sub‑task and wait for the user's go‑ahead.

## Task List Maintenance

1. **Update the task list as you work:**
   - Mark tasks and subtasks as completed (`[x]`) per the protocol above.
   - Add new tasks as they emerge.
2. **Maintain the "Relevant Files" section:**
   - List every file created or modified.
   - Give each file a one‑line description of its purpose.

## Context Maintenance

1. When implementing significant architectural changes to the codebase, ensure proper documentation by updating the Master Context Documents in the 'Planning/master\_context\_documents' folder. Follow these specific steps:  1. Verify the existence of the 'Planning/master\_context\_documents' directory structure. If the folder does not exist, create it immediately in the root of the repository.&#x20;
2. Examine the existing files within the 'Planning/master\_context\_documents' folder to understand the established naming convention and document format used by the project.&#x20;
3. Create a new Master Context Document file that follows the project's established nomenclature pattern, incorporating today's date in the filename to indicate this is an updated architectural documentation (e.g., 'mcd\_YYYY-MM-DD' format).&#x20;
4. In the newly created file, comprehensively document all architectural changes including:    - Modified module structures and their relationships    - Updated design patterns or architectural patterns    - Changes to data flow or control flow    - New dependencies or removed dependencies    - Updated configuration requirements    - Impact on existing functionality&#x20;
5. Ensure the documentation clearly explains the current state of the repository structure, providing enough context for future developers to understand the architectural decisions and implementation details.&#x20;
6. If this is the first Master Context Document being created for the project, establish the documentation standard by creating a comprehensive baseline architectural overview that serves as the foundation for future updates.
7. Systematically review and analyze the existing Master Context Documents to establish a comprehensive understanding of the current codebase structure, architectural patterns, and file modification protocols before implementing any updates. These documents are generated through the Context Distillation skill  and serve as authoritative reference materials. Their primary function is to provide AI models with a condensed, token-efficient snapshot that captures the project's complete architectural overview, data flow patterns, file responsibilities, interdependencies, and identified issues at a specific point in time. Leverage this structured context to ensure all file modifications align with established patterns, maintain consistency with the existing architecture, preserve data flow integrity, and address any documented issues or technical debt. Use these documents as the definitive guide for maintaining code quality standards, adhering to project conventions, and ensuring that new implementations integrate seamlessly with the existing codebase while supporting debugging efforts, system health assessments, and new feature development initiatives.

## AI Instructions

When working with task lists, the AI must:

1. Regularly update the task list file after finishing any significant work.
2. Follow the completion protocol:
   - Mark each finished **sub‑task** `[x]`.
   - Mark the **parent task** `[x]` once **all** its subtasks are `[x]`.
3. Add newly discovered tasks.
4. Keep "Relevant Files" accurate and up to date.
5. Before starting work, check which sub‑task is next.
6. After implementing a sub‑task, update the file and then pause for user approval.

