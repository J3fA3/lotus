"""
Task extraction agent using Ollama + Qwen 2.5
"""
import json
import time
import re
from typing import List, Dict, Optional
import httpx
from .prompts import get_task_extraction_prompt


class TaskExtractor:
    """AI-powered task extraction using local LLM"""

    def __init__(self, ollama_base_url: str, model: str):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)

    async def extract_tasks(self, input_text: str, assignee: str = "You") -> Dict:
        """
        Extract tasks from input text using Qwen 2.5

        Args:
            input_text: Text to analyze
            assignee: Default assignee for tasks

        Returns:
            Dict with tasks list and metadata
        """
        start_time = time.time()

        # Generate prompt
        prompts = get_task_extraction_prompt(input_text)

        # Call Ollama API
        try:
            response = await self._call_ollama(prompts["system"], prompts["user"])

            # Parse response
            tasks = self._parse_response(response, assignee)

            inference_time_ms = int((time.time() - start_time) * 1000)

            return {
                "tasks": tasks,
                "inference_time_ms": inference_time_ms,
                "model_used": self.model,
                "tasks_inferred": len(tasks)
            }
        except Exception as e:
            raise Exception(f"Task extraction failed: {str(e)}")

    async def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """Call Ollama API"""
        url = f"{self.ollama_base_url}/api/generate"

        # Combine prompts for Qwen 2.5 format
        full_prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_prompt}<|im_end|>
<|im_start|>assistant
"""

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower temp for more consistent JSON
                "top_p": 0.9,
                "num_predict": 1000,
            }
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except httpx.ConnectError:
            raise Exception("Cannot connect to Ollama. Make sure Ollama is running (ollama serve)")
        except httpx.HTTPError as e:
            raise Exception(f"Ollama API error: {str(e)}")

    def _parse_response(self, response: str, assignee: str) -> List[Dict]:
        """
        Parse LLM response and extract structured tasks

        Args:
            response: Raw LLM response
            assignee: Default assignee

        Returns:
            List of task dictionaries
        """
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            # Try to find just the tasks array
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                response = f'{{"tasks": {json_match.group(0)}}}'
            else:
                return []
        else:
            response = json_match.group(0)

        try:
            data = json.loads(response)
            tasks_data = data.get("tasks", [])

            # Convert to frontend format
            tasks = []
            for task in tasks_data:
                if not task.get("title"):
                    continue

                # Generate ID
                import uuid
                task_id = str(uuid.uuid4())

                # Build task object
                from datetime import datetime
                now = datetime.utcnow().isoformat()

                formatted_task = {
                    "id": task_id,
                    "title": task["title"],
                    "status": "todo",  # All inferred tasks start as todo
                    "assignee": assignee,
                    "startDate": None,
                    "dueDate": task.get("dueDate"),
                    "valueStream": task.get("valueStream"),
                    "description": task.get("description"),
                    "attachments": [],
                    "comments": [],
                    "createdAt": now,
                    "updatedAt": now
                }

                tasks.append(formatted_task)

            return tasks
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response: {response}")
            return []

    async def check_connection(self) -> bool:
        """Check if Ollama is accessible"""
        try:
            url = f"{self.ollama_base_url}/api/tags"
            response = await self.client.get(url)
            return response.status_code == 200
        except:
            return False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
