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
    
    # Constants
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_TOP_P = 0.9
    DEFAULT_MAX_TOKENS = 1000
    REQUEST_TIMEOUT = 120.0

    def __init__(self, ollama_base_url: str, model: str):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT)

    async def extract_tasks(self, input_text: str, assignee: str = "You") -> Dict:
        """
        Extract tasks from input text using Qwen 2.5

        Args:
            input_text: Text to analyze
            assignee: Default assignee for tasks

        Returns:
            Dict with tasks list and metadata
        
        Raises:
            Exception: If task extraction fails
        """
        if not input_text.strip():
            raise ValueError("Input text cannot be empty")
        
        start_time = time.time()

        try:
            # Generate prompt
            prompts = get_task_extraction_prompt(input_text)

            # Call Ollama API
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
        except (httpx.ConnectError, httpx.HTTPError) as e:
            raise Exception(f"Ollama connection error: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid input: {str(e)}")
        except Exception as e:
            raise Exception(f"Task extraction failed: {str(e)}")

    async def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """Call Ollama API with formatted prompts
        
        Args:
            system_prompt: System instruction prompt
            user_prompt: User query prompt
            
        Returns:
            LLM response text
            
        Raises:
            Exception: If Ollama connection fails or returns an error
        """
        url = f"{self.ollama_base_url}/api/generate"

        # Combine prompts for Qwen 2.5 format
        full_prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": self.DEFAULT_TEMPERATURE,
                "top_p": self.DEFAULT_TOP_P,
                "num_predict": self.DEFAULT_MAX_TOKENS,
            }
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except httpx.ConnectError:
            raise Exception("Cannot connect to Ollama. Ensure Ollama is running (ollama serve)")
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
        import uuid
        from datetime import datetime
        
        # Extract JSON from response
        json_text = self._extract_json_from_response(response)
        if not json_text:
            return []

        try:
            data = json.loads(json_text)
            tasks_data = data.get("tasks", [])

            # Convert to frontend format
            tasks = []
            now = datetime.utcnow().isoformat()
            
            for task in tasks_data:
                if not task.get("title"):
                    continue

                formatted_task = {
                    "id": str(uuid.uuid4()),
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
            print(f"Response: {response[:200]}...")  # Only print first 200 chars
            return []
    
    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """Extract JSON from LLM response
        
        Args:
            response: Raw LLM response
            
        Returns:
            Extracted JSON string or None
        """
        # Try to extract full JSON object
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json_match.group(0)
        
        # Try to find just the tasks array and wrap it
        array_match = re.search(r'\[[\s\S]*\]', response)
        if array_match:
            return f'{{"tasks": {array_match.group(0)}}}'
        
        return None

    async def check_connection(self) -> bool:
        """Check if Ollama is accessible
        
        Returns:
            True if Ollama is reachable, False otherwise
        """
        try:
            url = f"{self.ollama_base_url}/api/tags"
            response = await self.client.get(url)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self.client.aclose()
