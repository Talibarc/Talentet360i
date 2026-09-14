import models
from sqlalchemy import update


def audit(db, actor_id, action, entity_type, entity_id, *, subject_id=None, details=None):
    from function_scope import event_function
    details = dict(details or {})
    function = event_function(db, entity_type, entity_id, subject_id, details)
    if function:
        details["business_function"] = function
    row = models.AuditEvent(actor_id=actor_id, subject_id=subject_id, action=action,
                            entity_type=entity_type, entity_id=entity_id, details=details or {})
    db.add(row)
    db.flush()
    return row


def notify(db, recipient_id, title, message, event_type, entity_id=None, actor_id=None):
    row = models.Notification(recipient_id=recipient_id, title=title, message=message,
                              event_type=event_type, entity_id=entity_id)
    db.add(row)
    db.flush()
    audit(db, actor_id, "notification.created", "notification", row.id, subject_id=recipient_id,
          details={"event_type": event_type, "entity_id": entity_id})
    return row


def award_xp(db, employee_id, points, source_key, actor_id=None):
    if db.query(models.XpAward).filter_by(employee_id=employee_id, source_key=source_key).first():
        return False
    row = models.XpAward(employee_id=employee_id, points=points, source_key=source_key)
    db.add(row)
    db.flush()  # unique key makes concurrent retries roll back rather than award twice
    db.execute(update(models.User).where(models.User.id == employee_id)
               .values(xp_points=models.User.xp_points + points))
    audit(db, actor_id, "xp.awarded", "xp_award", row.id, subject_id=employee_id,
          details={"source_key": source_key, "points": points})
    return True
