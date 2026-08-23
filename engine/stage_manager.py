import enum
from typing import Dict, List, Optional, Callable

class InterviewStage(enum.Enum):
    STAGE_1_CLARIFY = 1   # Clarifying Questions & Constraints to Ask
    STAGE_2_APPROACH = 2  # Naive vs Optimal Approaches & High-Level Trade-offs
    STAGE_3_CODE = 3      # Optimal Code Solution, Complexity & Walkthrough
    STAGE_ALL_GLANCE = 4  # Full 3-Stage Glance Card

class StageManager:
    def __init__(self):
        self.current_stage = InterviewStage.STAGE_1_CLARIFY
        self.stage_results: Dict[InterviewStage, str] = {
            InterviewStage.STAGE_1_CLARIFY: "",
            InterviewStage.STAGE_2_APPROACH: "",
            InterviewStage.STAGE_3_CODE: "",
            InterviewStage.STAGE_ALL_GLANCE: ""
        }
        self.active_problem_statement = ""
        self.clarifications_resolved = False
        self._on_stage_change_callbacks: List[Callable[[InterviewStage], None]] = []

    def register_stage_listener(self, callback: Callable[[InterviewStage], None]):
        self._on_stage_change_callbacks.append(callback)

    def set_stage(self, stage: InterviewStage):
        self.current_stage = stage
        for cb in self._on_stage_change_callbacks:
            try:
                cb(stage)
            except Exception as e:
                print(f"[StageManager] Error in stage callback: {e}")

    def get_smart_next_stage(self) -> InterviewStage:
        """Determines the smart next stage when Ctrl+Space is tapped."""
        if not self.stage_results[InterviewStage.STAGE_1_CLARIFY]:
            return InterviewStage.STAGE_ALL_GLANCE
        elif self.current_stage == InterviewStage.STAGE_1_CLARIFY:
            return InterviewStage.STAGE_2_APPROACH
        elif self.current_stage == InterviewStage.STAGE_2_APPROACH:
            return InterviewStage.STAGE_3_CODE
        else:
            return InterviewStage.STAGE_ALL_GLANCE

    def store_stage_result(self, stage: InterviewStage, content: str):
        self.stage_results[stage] = content

    def get_stage_result(self, stage: InterviewStage) -> str:
        return self.stage_results.get(stage, "")

    def reset_for_new_problem(self, problem: str):
        self.active_problem_statement = problem
        self.clarifications_resolved = False
        for s in self.stage_results:
            self.stage_results[s] = ""
        self.set_stage(InterviewStage.STAGE_1_CLARIFY)
