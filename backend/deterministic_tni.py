"""Local narrative and course selection. No model or network dependency."""
from schemas import TniNarrative

NO_COURSE = "No validated course recommendation available."


def narrative(facts, resources):
    # Legacy synthetic exercises retain their fixture resources. Official workbook
    # recommendations are independently validated by the intelligence engine.
    return TniNarrative(
        summary=f"{facts['skill_name']}: provisional level {facts['current_level']} against target {facts['target_level']}; gap {facts['skill_gap']}.",
        development_focus="Review the assessment and mapped development needs with your manager.",
        next_steps=["Review the supplied mapping and its approval status before training.", "Review the assessment result with your manager."] if resources else [NO_COURSE, "Ask L&D to validate the learning mapping."],
        recommended_resource_ids=[r["resource_id"] for r in resources],
        limitations=["Calculated proficiency is separate from manager-confirmed official proficiency.",
                     "Resource mappings alone do not validate course suitability."])
