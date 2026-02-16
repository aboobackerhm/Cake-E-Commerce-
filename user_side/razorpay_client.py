# yourapp/utils/razorpay_client.py
import razorpay
from django.conf import settings

# Single global client instance (recommended)
razorpay_client = razorpay.Client(auth=(
    settings.RAZORPAY_KEY_ID,
    settings.RAZORPAY_KEY_SECRET
))

# Optional: You can add mode detection helper
def is_razorpay_test_mode():
    return settings.RAZORPAY_KEY_ID.startswith('rzp_test_')