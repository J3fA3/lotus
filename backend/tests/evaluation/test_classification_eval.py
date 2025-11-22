"""
Classification Agent Evaluation Tests - Phase 5
LLM-as-a-Judge Pattern

Uses Gemini to evaluate the quality of email classification decisions.

This implements the "LLM-as-a-judge" evaluation pattern where we use
a powerful LLM to assess the quality of another LLM's output.

Evaluation Criteria:
1. Classification Correctness (is_actionable, action_type)
2. Confidence Appropriateness (is confidence score calibrated?)
3. Reasoning Quality (is the explanation sound?)
4. Edge Case Handling (robustness to ambiguous inputs)
5. Consistency (same input → same output)
"""

import pytest
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from agents.email_classification import classify_email_content
from config.email_prompts import EmailClassification
from services.gemini_service import GeminiService


@dataclass
class EvaluationResult:
    """Result of LLM-as-a-judge evaluation."""
    test_case_id: str
    is_correct: bool
    quality_score: float  # 1-10
    confidence_appropriate: bool
    reasoning_quality_score: float  # 1-10
    judge_explanation: str
    classification_output: EmailClassification
    expected_output: Optional[Dict] = None


class ClassificationEvaluator:
    """Evaluates email classification agent using LLM-as-a-judge."""

    def __init__(self):
        self.gemini = GeminiService()
        self.evaluation_results: List[EvaluationResult] = []

    async def evaluate_single(
        self,
        test_case: Dict,
        expected: Optional[Dict] = None
    ) -> EvaluationResult:
        """Evaluate single classification against ground truth or expert judgment.

        Args:
            test_case: Test email data
            expected: Optional expected classification (ground truth)

        Returns:
            Evaluation result with scores and explanation
        """
        # Run classification
        result = await classify_email_content(
            email_id=test_case["id"],
            email_subject=test_case["subject"],
            email_sender=test_case["sender"],
            email_sender_name=test_case.get("sender_name", ""),
            email_sender_email=test_case.get("sender_email", ""),
            email_body=test_case["body"],
            email_snippet=test_case.get("snippet", test_case["body"][:100]),
            action_phrases=test_case.get("action_phrases", []),
            is_meeting_invite=test_case.get("is_meeting_invite", False)
        )

        classification = result["classification"]

        # Build judge prompt
        judge_prompt = self._build_judge_prompt(test_case, classification, expected)

        # Get judge evaluation
        judge_response = await self.gemini.generate_content(judge_prompt)

        # Parse judge response (expecting JSON)
        judge_eval = self._parse_judge_response(judge_response)

        # Create evaluation result
        eval_result = EvaluationResult(
            test_case_id=test_case["id"],
            is_correct=judge_eval.get("is_correct", False),
            quality_score=judge_eval.get("quality_score", 0.0),
            confidence_appropriate=judge_eval.get("confidence_appropriate", False),
            reasoning_quality_score=judge_eval.get("reasoning_quality_score", 0.0),
            judge_explanation=judge_eval.get("explanation", ""),
            classification_output=classification,
            expected_output=expected
        )

        self.evaluation_results.append(eval_result)
        return eval_result

    def _build_judge_prompt(
        self,
        test_case: Dict,
        classification: EmailClassification,
        expected: Optional[Dict]
    ) -> str:
        """Build LLM-as-a-judge evaluation prompt."""

        expected_section = ""
        if expected:
            expected_section = f"""

Ground Truth (Expected):
- Is Actionable: {expected.get('is_actionable')}
- Action Type: {expected.get('action_type')}
- Urgency: {expected.get('urgency')}
- Expected Confidence Range: {expected.get('confidence_range', 'N/A')}
"""

        prompt = f"""You are an expert evaluator assessing the quality of an email classification system.

Evaluate the following email classification:

EMAIL INPUT:
Subject: {test_case['subject']}
Sender: {test_case['sender']}
Body:
{test_case['body']}

CLASSIFICATION OUTPUT:
- Is Actionable: {classification.is_actionable}
- Action Type: {classification.action_type}
- Confidence: {classification.confidence:.2f}
- Urgency: {classification.urgency}
- Detected Project: {classification.detected_project or 'None'}
- Detected Deadline: {classification.detected_deadline or 'None'}
- Key Action Items: {', '.join(classification.key_action_items) if classification.key_action_items else 'None'}
- Reasoning: {classification.reasoning}
{expected_section}

EVALUATION CRITERIA:

1. **Classification Correctness** (is_correct: true/false)
   - Is the email correctly classified as actionable or not?
   - Is the action_type appropriate (task, meeting_prep, fyi, automated)?
   - Does urgency match the email content?

2. **Confidence Appropriateness** (confidence_appropriate: true/false)
   - Is the confidence score (0-1) calibrated correctly?
   - High confidence (>0.8) should be for clear, unambiguous requests
   - Medium confidence (0.5-0.8) for less certain cases
   - Low confidence (<0.5) for FYI/automated/ambiguous emails

3. **Reasoning Quality** (reasoning_quality_score: 1-10)
   - Does the reasoning explain the classification decision well?
   - Are the key factors mentioned?
   - Is it coherent and logical?

4. **Overall Quality** (quality_score: 1-10)
   - Overall assessment of classification quality
   - Consider all factors: correctness, confidence, reasoning

Provide your evaluation as JSON:

{{
  "is_correct": true/false,
  "confidence_appropriate": true/false,
  "quality_score": 1-10,
  "reasoning_quality_score": 1-10,
  "explanation": "Detailed explanation of your evaluation"
}}

Be objective and critical. Point out both strengths and weaknesses.
"""

        return prompt

    def _parse_judge_response(self, response: str) -> Dict:
        """Parse JSON response from judge LLM."""
        try:
            # Try to extract JSON from response
            # Response might have markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()

            return json.loads(json_str)

        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "is_correct": False,
                "confidence_appropriate": False,
                "quality_score": 0.0,
                "reasoning_quality_score": 0.0,
                "explanation": f"Failed to parse judge response: {response}"
            }

    def get_aggregate_metrics(self) -> Dict:
        """Get aggregate evaluation metrics across all test cases."""
        if not self.evaluation_results:
            return {}

        total = len(self.evaluation_results)
        correct = sum(1 for r in self.evaluation_results if r.is_correct)
        avg_quality = sum(r.quality_score for r in self.evaluation_results) / total
        avg_reasoning = sum(r.reasoning_quality_score for r in self.evaluation_results) / total
        confidence_appropriate = sum(1 for r in self.evaluation_results if r.confidence_appropriate)

        return {
            "total_evaluated": total,
            "accuracy": correct / total,
            "avg_quality_score": avg_quality,
            "avg_reasoning_quality_score": avg_reasoning,
            "confidence_calibration_rate": confidence_appropriate / total,
            "results": self.evaluation_results
        }


# ==============================================================================
# Test Cases with Ground Truth
# ==============================================================================

EVALUATION_TEST_CASES = [
    {
        "id": "eval_001",
        "subject": "URGENT: Review CRESCO dashboard by Friday EOD",
        "sender": "Alberto Martinez <alberto@cresco.com>",
        "body": "Hi Jef,\n\nCan you please review the CRESCO dashboard and provide feedback by Friday end of day? We need to finalize the metrics before the Spain launch.\n\nThanks,\nAlberto",
        "action_phrases": ["review", "provide feedback", "by Friday"],
        "is_meeting_invite": False,
        "expected": {
            "is_actionable": True,
            "action_type": "task",
            "urgency": "high",
            "confidence_range": (0.8, 1.0)
        }
    },
    {
        "id": "eval_002",
        "subject": "Weekly Newsletter - Product Updates",
        "sender": "no-reply@newsletter.com",
        "body": "Here are this week's product updates:\n\n1. New feature launched\n2. Bug fixes deployed\n\nClick here to unsubscribe.",
        "action_phrases": [],
        "is_meeting_invite": False,
        "expected": {
            "is_actionable": False,
            "action_type": "automated",
            "urgency": "low",
            "confidence_range": (0.5, 1.0)
        }
    },
    {
        "id": "eval_003",
        "subject": "Thoughts on the new design?",
        "sender": "designer@example.com",
        "body": "Hey, what do you think about the new design we discussed? Let me know when you can.",
        "action_phrases": ["let me know"],
        "is_meeting_invite": False,
        "expected": {
            "is_actionable": True,  # Ambiguous - could be True or False
            "action_type": "task",
            "urgency": "low",
            "confidence_range": (0.4, 0.7)  # Should have medium-low confidence
        }
    },
    {
        "id": "eval_004",
        "subject": "Meeting: Spain Launch Planning @ Monday 2pm",
        "sender": "pm@cresco.com",
        "body": "Please join us Monday at 2pm to discuss Spain launch strategy.\n\nZoom: https://zoom.us/j/123456789",
        "action_phrases": ["join", "discuss"],
        "is_meeting_invite": True,
        "expected": {
            "is_actionable": True,
            "action_type": "meeting_prep",
            "urgency": "medium",
            "confidence_range": (0.6, 0.9)
        }
    },
    {
        "id": "eval_005",
        "subject": "FYI - Deployment completed successfully",
        "sender": "devops@cresco.com",
        "body": "Just letting you know the deployment to production completed successfully. No action needed.",
        "action_phrases": [],
        "is_meeting_invite": False,
        "expected": {
            "is_actionable": False,
            "action_type": "fyi",
            "urgency": "low",
            "confidence_range": (0.6, 1.0)
        }
    },
    {
        "id": "eval_006",
        "subject": "Action Items from Meeting",
        "sender": "pm@cresco.com",
        "body": """Following up from today's meeting:

1. Jef: Update CRESCO dashboard by Friday
2. Jef: Review Moodboard export by Monday
3. Jef: Schedule follow-up with Alberto

Please confirm you've seen this.""",
        "action_phrases": ["update", "review", "schedule", "by Friday", "by Monday"],
        "is_meeting_invite": False,
        "expected": {
            "is_actionable": True,
            "action_type": "task",
            "urgency": "high",
            "confidence_range": (0.85, 1.0)  # Very clear action items
        }
    }
]


# ==============================================================================
# Evaluation Tests
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_classification_quality_eval_high_confidence():
    """Evaluate high-confidence classification quality."""

    evaluator = ClassificationEvaluator()

    # Test high-confidence case
    test_case = EVALUATION_TEST_CASES[0]  # URGENT CRESCO review
    expected = test_case["expected"]

    result = await evaluator.evaluate_single(test_case, expected)

    # Judge should confirm this is correct
    assert result.is_correct == True
    assert result.quality_score >= 7.0  # Should score well
    assert result.confidence_appropriate == True

    print(f"\nEvaluation for {test_case['id']}:")
    print(f"  Quality Score: {result.quality_score}/10")
    print(f"  Reasoning Quality: {result.reasoning_quality_score}/10")
    print(f"  Judge Explanation: {result.judge_explanation}")


@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_classification_quality_eval_automated():
    """Evaluate automated/newsletter classification quality."""

    evaluator = ClassificationEvaluator()

    # Test automated case
    test_case = EVALUATION_TEST_CASES[1]  # Newsletter
    expected = test_case["expected"]

    result = await evaluator.evaluate_single(test_case, expected)

    # Should correctly identify as automated
    assert result.classification_output.action_type in ["automated", "fyi"]
    assert result.classification_output.is_actionable == False

    print(f"\nEvaluation for {test_case['id']}:")
    print(f"  Classified as: {result.classification_output.action_type}")
    print(f"  Quality Score: {result.quality_score}/10")
    print(f"  Judge Explanation: {result.judge_explanation}")


@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_classification_quality_eval_ambiguous():
    """Evaluate ambiguous case handling."""

    evaluator = ClassificationEvaluator()

    # Test ambiguous case
    test_case = EVALUATION_TEST_CASES[2]  # "Thoughts on design?"
    expected = test_case["expected"]

    result = await evaluator.evaluate_single(test_case, expected)

    # Confidence should be in medium-low range for ambiguous
    assert 0.3 <= result.classification_output.confidence <= 0.8

    # Judge should note confidence is appropriate for ambiguity
    print(f"\nEvaluation for {test_case['id']}:")
    print(f"  Confidence: {result.classification_output.confidence:.2f}")
    print(f"  Confidence Appropriate: {result.confidence_appropriate}")
    print(f"  Judge Explanation: {result.judge_explanation}")


@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_classification_quality_eval_batch():
    """Evaluate entire test suite and compute aggregate metrics."""

    evaluator = ClassificationEvaluator()

    # Evaluate all test cases
    for test_case in EVALUATION_TEST_CASES:
        expected = test_case.get("expected")
        await evaluator.evaluate_single(test_case, expected)

    # Get aggregate metrics
    metrics = evaluator.get_aggregate_metrics()

    print("\n" + "=" * 60)
    print("AGGREGATE EVALUATION METRICS")
    print("=" * 60)
    print(f"Total Evaluated: {metrics['total_evaluated']}")
    print(f"Accuracy: {metrics['accuracy']:.2%}")
    print(f"Avg Quality Score: {metrics['avg_quality_score']:.1f}/10")
    print(f"Avg Reasoning Quality: {metrics['avg_reasoning_quality_score']:.1f}/10")
    print(f"Confidence Calibration Rate: {metrics['confidence_calibration_rate']:.2%}")
    print("=" * 60)

    # Performance targets
    assert metrics["accuracy"] >= 0.80  # 80% accuracy
    assert metrics["avg_quality_score"] >= 6.5  # Avg quality 6.5+/10
    assert metrics["confidence_calibration_rate"] >= 0.70  # 70% confidence calibration


@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_classification_consistency():
    """Test classification consistency - same input should produce same output."""

    test_case = EVALUATION_TEST_CASES[0]

    # Run classification 3 times
    results = []
    for i in range(3):
        result = await classify_email_content(
            email_id=f"{test_case['id']}_run_{i}",
            email_subject=test_case["subject"],
            email_sender=test_case["sender"],
            email_sender_name=test_case.get("sender_name", ""),
            email_sender_email=test_case.get("sender_email", ""),
            email_body=test_case["body"],
            email_snippet=test_case.get("snippet", test_case["body"][:100]),
            action_phrases=test_case.get("action_phrases", []),
            is_meeting_invite=test_case.get("is_meeting_invite", False)
        )
        results.append(result["classification"])

    # Check consistency
    action_types = [r.action_type for r in results]
    confidences = [r.confidence for r in results]
    is_actionables = [r.is_actionable for r in results]

    # All should have same action_type
    assert len(set(action_types)) == 1, f"Inconsistent action_types: {action_types}"

    # All should have same is_actionable
    assert len(set(is_actionables)) == 1, f"Inconsistent is_actionable: {is_actionables}"

    # Confidence should be within 0.1 range (some variance is acceptable)
    confidence_variance = max(confidences) - min(confidences)
    assert confidence_variance <= 0.15, f"High confidence variance: {confidences}"

    print(f"\nConsistency Test Results:")
    print(f"  Action Types: {action_types}")
    print(f"  Confidences: {[f'{c:.2f}' for c in confidences]}")
    print(f"  Confidence Variance: {confidence_variance:.3f}")


@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_classification_reasoning_quality():
    """Evaluate reasoning quality using LLM-as-a-judge."""

    evaluator = ClassificationEvaluator()

    # Test cases specifically for reasoning evaluation
    reasoning_test_cases = [
        EVALUATION_TEST_CASES[0],  # High confidence task
        EVALUATION_TEST_CASES[5],  # Multiple action items
    ]

    for test_case in reasoning_test_cases:
        result = await evaluator.evaluate_single(test_case, test_case.get("expected"))

        # Reasoning quality should be good
        assert result.reasoning_quality_score >= 6.0, \
            f"Low reasoning quality ({result.reasoning_quality_score}) for {test_case['id']}"

        print(f"\nReasoning Evaluation for {test_case['id']}:")
        print(f"  Reasoning Quality Score: {result.reasoning_quality_score}/10")
        print(f"  Actual Reasoning: {result.classification_output.reasoning}")
        print(f"  Judge Feedback: {result.judge_explanation}")


@pytest.mark.asyncio
@pytest.mark.evaluation
async def test_classification_edge_case_robustness():
    """Test robustness to edge cases using LLM-as-a-judge."""

    evaluator = ClassificationEvaluator()

    edge_cases = [
        {
            "id": "edge_001",
            "subject": "",  # Empty subject
            "sender": "test@example.com",
            "body": "Please review this.",
            "action_phrases": ["review"],
            "is_meeting_invite": False,
            "expected": {
                "is_actionable": True,
                "action_type": "task",
                "urgency": "low",
                "confidence_range": (0.5, 0.9)
            }
        },
        {
            "id": "edge_002",
            "subject": "Test 🔥 with émojis",
            "sender": "test@example.com",
            "body": "Body with émojis 🎉 and spëcial çhars",
            "action_phrases": [],
            "is_meeting_invite": False,
            "expected": {
                "is_actionable": False,
                "action_type": "fyi",
                "urgency": "low",
                "confidence_range": (0.3, 0.8)
            }
        }
    ]

    for test_case in edge_cases:
        result = await evaluator.evaluate_single(test_case, test_case.get("expected"))

        # Should handle edge case without crashing
        assert result is not None
        assert result.classification_output is not None

        print(f"\nEdge Case {test_case['id']} Evaluation:")
        print(f"  Quality Score: {result.quality_score}/10")
        print(f"  Handled Correctly: {result.is_correct}")
