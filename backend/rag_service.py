import re
from typing import Any
 
from excel_loader import FINANCE_FILE, read_sheet
 
 
STOP_WORDS = {
    "and",
    "or",
    "the",
    "for",
    "of",
    "with",
    "to",
}
 
 
def _tokens(value: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", value.lower())
    return {word for word in words if word not in STOP_WORDS}
 
 
def retrieve_finance_context(
    role_name: str,
    skill_name: str,
) -> dict[str, Any]:
    roles = read_sheet(
        FINANCE_FILE,
        "Role_Descriptions",
        3,
    )
    skills = read_sheet(
        FINANCE_FILE,
        "Skill_Master",
        3,
    )
    mappings = read_sheet(
        FINANCE_FILE,
        "Role_Skill_Map",
        3,
    )
 
    role = next(
        (
            row
            for row in roles
            if str(row.get("role_name", "")).lower()
            == role_name.lower()
        ),
        None,
    )
 
    if role is None:
        raise ValueError(
            f"Role '{role_name}' was not found in finance data."
        )
 
    role_id = role["role_id"]
 
    role_mappings = [
        row
        for row in mappings
        if row.get("role_id") == role_id
    ]
 
    requested_tokens = _tokens(skill_name)
    scored_mappings = []
 
    for mapping in role_mappings:
        mapped_tokens = _tokens(str(mapping.get("skill", "")))
        score = len(requested_tokens & mapped_tokens)
        scored_mappings.append((score, mapping))
 
    scored_mappings.sort(
        key=lambda item: item[0],
        reverse=True,
    )
 
    matched_mappings = [
        mapping
        for score, mapping in scored_mappings
        if score > 0
    ][:2]
 
    skill_lookup = {
        row.get("skill_id"): row
        for row in skills
    }
 
    matched_skills = []
 
    for mapping in matched_mappings:
        skill = skill_lookup.get(mapping.get("skill_id"), {})
        level = mapping.get("target_proficiency_level")
        indicator_column = f"L{level}_indicator"
 
        matched_skills.append(
            {
                "skill_id": mapping.get("skill_id"),
                "skill": mapping.get("skill"),
                "target_level": level,
                "capability": mapping.get("capability"),
                "level_indicator": skill.get(indicator_column),
                "source_file": mapping.get("source_file"),
            }
        )
 
    return {
        "role_id": role_id,
        "role_name": role.get("role_name"),
        "role_summary": role.get("role_summary_or_positioning"),
        "responsibilities": role.get("responsibility_extract"),
        "success_measures": role.get(
            "output_or_success_measure_extract"
        ),
        "matched_skills": matched_skills,
        "rag_source": (
            "Finance role profile, Skill Master and Role Skill Map"
        ),
    }
 
 
def build_finance_rag_context(
    role_name: str,
    skill_name: str,
) -> str:
    data = retrieve_finance_context(role_name, skill_name)
 
    skill_lines = []
 
    for skill in data["matched_skills"]:
        skill_lines.append(
            f"- Skill: {skill['skill']}; "
            f"Target level: L{skill['target_level']}; "
            f"Expected behaviour: {skill['level_indicator']}"
        )
 
    return "\n".join(
        [
            f"Source: {data['rag_source']}",
            f"Role: {data['role_name']}",
            f"Role summary: {data['role_summary']}",
            f"Responsibilities: {data['responsibilities']}",
            f"Success measures: {data['success_measures']}",
            "Retrieved skill context:",
            *skill_lines,
        ]
    )