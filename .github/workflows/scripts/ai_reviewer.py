#!/usr/bin/env python3
import os
import logging
import openai
from datetime import datetime

logger = logging.getLogger(__name__)


class AICodeReviewer:
    """
    Handles all AI-based code analysis for the PR reviewer
    """

    def __init__(self, api_key, model="gpt-4-turbo"):
        """
        Initialize the AI code reviewer

        Args:
            api_key (str): OpenAI API key
            model (str): OpenAI model to use
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def analyze_file_change(self, filename, patch, max_tokens=800):
        """
        Analyze a code change using AI

        Args:
            filename (str): Name of the file being changed
            patch (str): Diff patch showing the changes
            max_tokens (int): Maximum tokens for the response

        Returns:
            str: AI analysis of the code changes
        """
        file_extension = os.path.splitext(filename)[1]
        language = self._determine_language(file_extension)

        # Create a prompt for the AI
        prompt = f"""
        You are reviewing a GitHub Pull Request.

        File: {filename}
        Language: {language}

        Here is the patch (the changes made in this PR):
        ```
        {patch}
        ```

        Please review this code change and provide:
        1. A brief assessment of what the change is doing
        2. Any potential bugs, vulnerabilities, or issues
        3. Style suggestions and best practices
        4. Performance considerations if applicable

        Format your review as a clear, helpful GitHub comment with markdown formatting.
        Be specific and constructive. Focus on the most important issues.
        If the code looks good, briefly say so and highlight any particularly good aspects.
        """

        # Call the AI model
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You are an expert code reviewer. Be concise, specific, and constructive."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.4  # Lower temperature for more consistent reviews
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            return f"⚠️ AI review failed: {str(e)}"

    def generate_pr_summary(self, pr_title, pr_description, files_changed, base_branch, head_branch):
        """
        Generate an overall summary of the PR

        Args:
            pr_title (str): PR title
            pr_description (str): PR description
            files_changed (list): List of changed file paths
            base_branch (str): Base branch name
            head_branch (str): Head branch name

        Returns:
            str: AI-generated PR summary
        """
        files_list = "\n".join([f"- `{f}`" for f in files_changed])

        prompt = f"""
        You are reviewing a GitHub Pull Request.

        PR Title: {pr_title}
        PR Description: {pr_description}
        From Branch: {head_branch}
        To Branch: {base_branch}

        Files changed ({len(files_changed)}):
        {files_list}

        Please provide:
        1. A concise summary of what this PR appears to be doing
        2. Any concerns about the overall approach or scope
        3. General suggestions for the author

        Format your response as a clear, constructive GitHub comment with markdown formatting.
        Begin with "## AI Review Summary" as a heading.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system",
                     "content": "You are an expert code reviewer who specializes in providing helpful PR summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.5
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI summary generation failed: {str(e)}")
            return f"## AI Review Summary\n\nFailed to generate summary: {str(e)}"

    def analyze_code_quality(self, code, language):
        """
        Analyze code quality without context of changes

        Args:
            code (str): Full code content
            language (str): Programming language

        Returns:
            str: Code quality analysis
        """
        prompt = f"""
        Analyze the quality of this {language} code:

        ```
        {code}
        ```

        Focus on:
        1. Code structure and organization
        2. Potential bugs or issues
        3. Complexity and maintainability
        4. Security considerations

        Provide specific recommendations for improvement.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert code quality analyzer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.4
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Code quality analysis failed: {str(e)}")
            return f"Code quality analysis failed: {str(e)}"

    def _determine_language(self, file_extension):
        """
        Map file extension to language name

        Args:
            file_extension (str): File extension including dot

        Returns:
            str: Human-readable language name
        """
        mapping = {
            ".py": "Python",
            ".js": "JavaScript",
            ".jsx": "React JavaScript",
            ".ts": "TypeScript",
            ".tsx": "React TypeScript",
            ".java": "Java",
            ".go": "Go",
            ".rb": "Ruby",
            ".php": "PHP",
            ".c": "C",
            ".cpp": "C++",
            ".cs": "C#",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".md": "Markdown",
            ".json": "JSON",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".toml": "TOML",
            ".sql": "SQL",
            ".sh": "Shell",
            ".bash": "Bash",
            ".rs": "Rust",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".dart": "Dart",
            ".lua": "Lua"
        }
        return mapping.get(file_extension.lower(), "Unknown")