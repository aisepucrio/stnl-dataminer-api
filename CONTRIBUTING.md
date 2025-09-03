Contribution Workflow

1. Create a New Branch

    Before you start working, create a new branch from the main branch. Use a descriptive name for your branch, like feature/add-user-login or fix/button-color.

    ```
    # Pull the latest changes from the main branch
    git pull origin main

    # Create your new branch
    git checkout -b your-branch-name
    ```

2. Code Your Changes

    Make your changes in the new branch. Be sure to write clear, concise code and include comments where necessary.

3. Commit Your Changes

    Once you're ready, commit your changes with a clear and descriptive commit message. You can make multiple commits if it makes your change history more descriptive.

    ```
    git add .
    git commit -m "feat: a brief description of your changes"
    ```

4. Push to Your Branch

    Push your branch to the remote repository.

    `git push origin your-branch-name`

5. Create a Pull Request (PR)

   Go to the repository on GitHub and create a new pull request.

   - Base Branch: The base branch should always be main.
   - Title and Description: Give your PR a clear title that summarizes the changes, and provide a detailed description of what the PR does, why it's needed, and any relevant context.
   - Assignees: You can assign the PR to one or more people for review. GitHub will often suggest reviewers who have worked on the relevant files.
   - Review Requirements: Your PR needs at least one approval from a reviewer before it can be merged.
   - Checks: If there are automated checks, they should pass before the PR can be merged.
