import re
import time
from typing import List, Tuple

AFFIRMATION_WORDS = {
    "yeah", "yes", "yep", "right", "uh-huh", "uh huh", "got it", "okay", "ok",
    "sure", "cool", "makes sense", "understood", "all right", "alright", "i see",
    "gotcha", "yup", "no problem", "sounds good", "yeah yeah", "yes yes", "ok ok"
}

class TranscriptReconciler:
    def __init__(self, max_history_turns: int = 10):
        self.max_history_turns = max_history_turns
        self.finalized_clauses: List[str] = []
        self.current_interim: str = ""
        self.history: List[Tuple[str, str]] = []
        self.last_update_time = time.time()

    def add_final(self, text: str, speaker: str = "Interviewer"):
        """Adds a confirmed, finalized speech clause."""
        cleaned = text.strip()
        if not cleaned:
            return

        # Check candidate affirmation filter
        if speaker.lower() in ("candidate", "speaker", "user") and self.is_affirmation(cleaned):
            # Ignore brief affirmation to prevent cluttering interviewer question
            return

        self.finalized_clauses.append(cleaned)
        self.current_interim = ""
        self.last_update_time = time.time()

        if len(self.finalized_clauses) > 20:
            self.finalized_clauses = self.finalized_clauses[-20:]

    def set_interim(self, text: str):
        """Sets the current unfinalized interim phrase."""
        self.current_interim = text.strip()
        self.last_update_time = time.time()

    def get_live_display_text(self) -> str:
        """Returns clean text for the live transcription pill on HUD."""
        full = " ".join(self.finalized_clauses[-3:])
        if self.current_interim:
            full = f"{full} {self.current_interim}".strip()
        return full

    def get_reconciled_question(self) -> str:
        """
        Deduplicates and merges FinalizedBuffer + InterimBuffer for instant hotkey trigger.
        Ensures the trailing clause of the interviewer's question is never lost.
        """
        if not self.finalized_clauses and not self.current_interim:
            return ""

        final_text = " ".join(self.finalized_clauses).strip()
        if not self.current_interim:
            return final_text

        if not final_text:
            return self.current_interim

        # Word-level overlap deduplication
        final_words = final_text.split()
        interim_words = self.current_interim.split()

        # Check for overlap of 1 to min(6, len(final_words), len(interim_words)) words
        max_overlap = min(6, len(final_words), len(interim_words))
        overlap_len = 0

        for k in range(max_overlap, 0, -1):
            if [w.lower() for w in final_words[-k:]] == [w.lower() for w in interim_words[:k]]:
                overlap_len = k
                break

        if overlap_len > 0:
            merged = " ".join(final_words + interim_words[overlap_len:])
        else:
            merged = f"{final_text} {self.current_interim}"

        return merged.strip()

    def is_affirmation(self, text: str) -> bool:
        """Determines if an utterance is merely a short candidate verbal acknowledgment."""
        words = re.findall(r"\w+", text.lower())
        if not words or len(words) > 4:
            return False
        clean_text = " ".join(words)
        return (
            clean_text in AFFIRMATION_WORDS or
            all(w in AFFIRMATION_WORDS for w in words)
        )

    def archive_turn(self, question: str, answer_summary: str):
        """Saves a completed Q&A turn into conversational history."""
        self.history.append(("Interviewer", question))
        self.history.append(("Candidate", answer_summary))
        if len(self.history) > self.max_history_turns * 2:
            self.history = self.history[-(self.max_history_turns * 2):]
        self.clear_current()

    def clear_current(self):
        """Clears current active turn buffers."""
        self.finalized_clauses.clear()
        self.current_interim = ""
        self.last_update_time = time.time()
