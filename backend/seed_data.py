"""
Training Content Repository seed data (Modules / Quests / Assessments box).
Idempotent: safe to call on every startup.
"""
from sqlalchemy.orm import Session

from backend import models

MODULES = [
    {"id": "mod_safety", "title": "Workplace Safety", "skill": "workplace_safety",
     "description": "Hazard recognition and safe-work-practice scenarios."},
    {"id": "mod_service", "title": "Customer Service Excellence", "skill": "customer_service",
     "description": "De-escalation and service-recovery scenarios."},
    {"id": "mod_privacy", "title": "Data Privacy & Compliance", "skill": "data_privacy",
     "description": "Handling personal data responsibly under company policy."},
    {"id": "mod_onboarding", "title": "New Employee Onboarding", "skill": "onboarding_compliance",
     "description": "Policy awareness and correct escalation during a new hire's first weeks."},
]

QUESTS = [
    # Workplace Safety
    {"id": "q_safety_1", "module_id": "mod_safety", "skill": "workplace_safety", "difficulty": 1, "kind": "quiz",
     "prompt": "You see a colleague lifting a heavy box with a bent back. What should you do first?",
     "options": ["Tell them to bend their knees and offer help", "Ignore it, not your job",
                 "Report them to HR immediately", "Take a photo for later"],
     "correct_index": 0},
    {"id": "q_safety_2", "module_id": "mod_safety", "skill": "workplace_safety", "difficulty": 2, "kind": "quiz",
     "prompt": "You find a liquid spill on the warehouse floor with no warning sign. What's the correct first action?",
     "options": ["Walk around it and continue", "Cordon it off / place a warning sign, then report it",
                 "Mop it up without telling anyone", "Wait for someone else to notice"],
     "correct_index": 1},
    {"id": "q_safety_3", "module_id": "mod_safety", "skill": "workplace_safety", "difficulty": 3, "kind": "scenario",
     "prompt": "An emergency exit is partially blocked by stacked pallets during a busy shift. What is the appropriate response?",
     "options": ["Clear it immediately and escalate to facilities", "Leave it, it's only partially blocked",
                 "Note it for the next safety audit in a month", "Ask a colleague to remember to move it later"],
     "correct_index": 0},
    {"id": "q_safety_4", "module_id": "mod_safety", "skill": "workplace_safety", "difficulty": 4, "kind": "scenario",
     "prompt": "Your team is behind schedule and a supervisor suggests skipping a required safety check to save time. What do you do?",
     "options": ["Follow the required safety check and flag the schedule pressure to management",
                 "Skip it since the supervisor approved it", "Skip it quietly and hope nothing happens",
                 "Complain to coworkers but do nothing else"],
     "correct_index": 0},
    # Customer Service
    {"id": "q_service_1", "module_id": "mod_service", "skill": "customer_service", "difficulty": 1, "kind": "quiz",
     "prompt": "A customer is polite but confused about how to use a product. What's the best response?",
     "options": ["Patiently walk them through it step by step", "Tell them to read the manual",
                 "Transfer them without explanation", "Rush the explanation"],
     "correct_index": 0},
    {"id": "q_service_2", "module_id": "mod_service", "skill": "customer_service", "difficulty": 2, "kind": "quiz",
     "prompt": "A customer is raising their voice about a late delivery. What is the best de-escalation response?",
     "options": ["Match their tone to show you understand", "Acknowledge the frustration calmly and offer a concrete next step",
                 "Put them on hold indefinitely", "Argue that the delay wasn't your fault"],
     "correct_index": 1},
    {"id": "q_service_3", "module_id": "mod_service", "skill": "customer_service", "difficulty": 3, "kind": "scenario",
     "prompt": "A client asks for a refund outside of policy, citing a competitor's more flexible terms. How do you respond?",
     "options": ["Explain the policy clearly and offer any available alternative within policy",
                 "Grant the refund anyway to keep them happy", "Refuse flatly with no explanation",
                 "Tell them to complain to your manager"],
     "correct_index": 0},
    {"id": "q_service_4", "module_id": "mod_service", "skill": "customer_service", "difficulty": 4, "kind": "scenario",
     "prompt": "A long-time customer sends an angry message with three unrelated complaints bundled together. What's the best first step?",
     "options": ["Acknowledge all concerns and ask which is most urgent to resolve first",
                 "Respond only to the first complaint", "Ask them to submit three separate tickets",
                 "Escalate without reading closely"],
     "correct_index": 0},
    # Data Privacy
    {"id": "q_privacy_1", "module_id": "mod_privacy", "skill": "data_privacy", "difficulty": 1, "kind": "quiz",
     "prompt": "A colleague asks you to email a spreadsheet of customer personal data to their personal Gmail account. What do you do?",
     "options": ["Decline and direct them to the approved secure channel", "Send it since they're a colleague",
                 "Send it but remove one column", "Ask your manager after sending it"],
     "correct_index": 0},
    {"id": "q_privacy_2", "module_id": "mod_privacy", "skill": "data_privacy", "difficulty": 2, "kind": "quiz",
     "prompt": "You discover a shared drive with unrestricted access to employee salary data. What is the correct escalation?",
     "options": ["Report it to IT security / data protection officer immediately", "Fix the permissions yourself quietly",
                 "Ignore it, it's not your department", "Mention it casually in a team chat"],
     "correct_index": 0},
    {"id": "q_privacy_3", "module_id": "mod_privacy", "skill": "data_privacy", "difficulty": 3, "kind": "scenario",
     "prompt": "A vendor requests a sample of real customer data 'just to test integration'. What should you check first?",
     "options": ["Whether anonymized/synthetic test data can be used instead, per policy",
                 "Whether the vendor has a good reputation", "Whether the request is in writing",
                 "Whether the vendor is paying for the service"],
     "correct_index": 0},
    {"id": "q_privacy_4", "module_id": "mod_privacy", "skill": "data_privacy", "difficulty": 4, "kind": "scenario",
     "prompt": "An internal dashboard accidentally displays another employee's personal training records to you. What do you do?",
     "options": ["Stop viewing it and report the access issue immediately",
                 "Read through it since it was already shown to you", "Screenshot it as evidence",
                 "Mention it to the employee directly"],
     "correct_index": 0},
    # New Employee Onboarding (4th vertical - reuses the same engine unmodified,
    # demonstrating the framework generalizes beyond its original 3 verticals, R2)
    {"id": "q_onboarding_1", "module_id": "mod_onboarding", "skill": "onboarding_compliance", "difficulty": 1, "kind": "quiz",
     "prompt": "It's your first week and you're unsure which system holds the official expense policy. What should you do?",
     "options": ["Check the onboarding portal / ask your manager for the official source", "Guess based on a former employer's policy",
                 "Ask a random coworker in chat and assume it's correct", "Skip the expense claim entirely"],
     "correct_index": 0},
    {"id": "q_onboarding_2", "module_id": "mod_onboarding", "skill": "onboarding_compliance", "difficulty": 2, "kind": "quiz",
     "prompt": "A senior colleague asks you to skip the mandatory security training 'since it's just a formality'. What do you do?",
     "options": ["Ignore them and complete it since it's just a formality", "Complete the mandatory training regardless and mention the comment if it recurs",
                 "Skip it to avoid conflict with a senior colleague", "Mark it complete without doing it"],
     "correct_index": 1},
    {"id": "q_onboarding_3", "module_id": "mod_onboarding", "skill": "onboarding_compliance", "difficulty": 3, "kind": "scenario",
     "prompt": "You are asked to sign off on a process you were never trained on, because 'everyone does it this way'. What is the appropriate response?",
     "options": ["Ask for proper training or written guidance before signing off", "Sign off anyway since others do",
                 "Sign off but tell no one", "Refuse to do the task at all without escalating"],
     "correct_index": 0},
    {"id": "q_onboarding_4", "module_id": "mod_onboarding", "skill": "onboarding_compliance", "difficulty": 4, "kind": "scenario",
     "prompt": "During onboarding you notice a documented process conflicts with what your team actually does day-to-day. What should you do?",
     "options": ["Raise the discrepancy with your manager or the process owner for clarification",
                 "Follow the undocumented team habit since it's more common", "Follow the document strictly and say nothing",
                 "Ignore both and do whatever seems easiest"],
     "correct_index": 0},
]


def seed(db: Session) -> None:
    """Idempotent per-row: safe to call on every startup, and safe to add new
    modules/quests later without wiping or skipping seeding on an existing DB."""
    existing_module_ids = {m.id for m in db.query(models.Module.id).all()}
    for m in MODULES:
        if m["id"] not in existing_module_ids:
            db.add(models.Module(**m))

    existing_quest_ids = {q.id for q in db.query(models.Quest.id).all()}
    for q in QUESTS:
        if q["id"] not in existing_quest_ids:
            db.add(models.Quest(**q))

    db.commit()
