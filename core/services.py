from .models import AuditLog


def log_action(actor, action, target_type="", target_id="", metadata=None):
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else "",
        metadata=metadata or {},
    )
