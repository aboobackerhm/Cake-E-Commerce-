from django.db.models.signals import post_save
from django.dispatch import receiver
from admin_panel.models import Order, Wallet, WalletTransaction  # adjust imports

@receiver(post_save, sender=Order)
def handle_order_refund(sender, instance, created, **kwargs):
    if created:
        return

    # Case 1: Order Cancelled (immediate refund to wallet)
    if instance.status == 'CANCELLED' and instance.previous_status != 'CANCELLED':
        if instance.paid_amount > 0:
            wallet, _ = Wallet.objects.get_or_create(user=instance.user)
            wallet.credit(
                amount=instance.paid_amount,
                description=f"Refund for cancelled order #{instance.id}",
                related_order=instance
            )
            # Optional: mark order as refunded
            instance.refunded_amount = instance.paid_amount
            instance.save(update_fields=['refunded_amount'])

    # Case 2: Return approved by admin (refund after approval)
    if instance.status == 'RETURN_APPROVED' and instance.previous_status != 'RETURN_APPROVED':
        if instance.paid_amount > 0:
            wallet, _ = Wallet.objects.get_or_create(user=instance.user)
            wallet.credit(
                amount=instance.paid_amount,
                description=f"Refund for approved return of order #{instance.id}",
                related_order=instance
            )
            instance.refunded_amount = instance.paid_amount
            instance.save(update_fields=['refunded_amount'])