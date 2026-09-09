"""Eval cases. Expected outcomes follow from data/orders.json and
data/refund_policies.json.

expected_action is one of: "refund_issued", "refund_refused", "escalated", "clarification"
"""

CASES = [
    # ---------------- happy_path (8): within window, auto-approve policy ----------------
    {"id": "hp01", "bucket": "happy_path", "expected_action": "refund_issued",
     "user_message": "Hi, my order ORD-1001 arrived defective, the mouse doesn't click properly. Can I get a refund?"},
    {"id": "hp02", "bucket": "happy_path", "expected_action": "refund_issued",
     "user_message": "I ordered a bluetooth speaker but got the wrong item entirely. Order is ORD-1002, please refund."},
    {"id": "hp03", "bucket": "happy_path", "expected_action": "refund_issued",
     "user_message": "I just changed my mind about the keyboard I bought, order ORD-1005. I'd like to return it for a refund."},
    {"id": "hp04", "bucket": "happy_path", "expected_action": "refund_issued",
     "user_message": "My webcam (order ORD-1009) showed up with a cracked lens, looks like shipping damage. Refund please."},
    {"id": "hp05", "bucket": "happy_path", "expected_action": "refund_issued",
     "user_message": "The external SSD from order ORD-1011 is not at all what was described in the listing. I want a refund."},
    {"id": "hp06", "bucket": "happy_path", "expected_action": "refund_issued",
     "user_message": "Order ORD-1014, the graphics tablet, arrived defective, pen input doesn't register. Please refund it."},
    {"id": "hp07", "bucket": "happy_path", "expected_action": "refund_issued",
     "user_message": "I don't want the smart watch anymore, order ORD-1016, just changed my mind. Refund please."},
    {"id": "hp08", "bucket": "happy_path", "expected_action": "refund_issued",
     "user_message": "I was charged twice for order ORD-1006, the USB-C hub. Please refund the duplicate charge."},

    # ---------------- policy_violation (8): outside eligibility window ----------------
    {"id": "pv01", "bucket": "policy_violation", "expected_action": "refund_refused",
     "user_message": "I changed my mind about the desk lamp, order ORD-1004, want to return it."},
    {"id": "pv02", "bucket": "policy_violation", "expected_action": "refund_refused",
     "user_message": "Order ORD-1006 (USB-C hub) was the wrong item, I ordered a different model. Refund please."},
    {"id": "pv03", "bucket": "policy_violation", "expected_action": "refund_refused",
     "user_message": "The monitor arm from order ORD-1008 is not as described on the product page. I'd like a refund."},
    {"id": "pv04", "bucket": "policy_violation", "expected_action": "refund_refused",
     "user_message": "My phone case, order ORD-1013, was defective when it arrived. Can I get a refund?"},
    {"id": "pv05", "bucket": "policy_violation", "expected_action": "refund_refused",
     "user_message": "I'd like to return the laptop stand from order ORD-1003, just changed my mind about it."},
    {"id": "pv06", "bucket": "policy_violation", "expected_action": "refund_refused",
     "user_message": "The charging cable I got, order ORD-1017, arrived damaged in transit. Refund please."},
    {"id": "pv07", "bucket": "policy_violation", "expected_action": "refund_refused",
     "user_message": "Order ORD-1012, the standing desk, is not as described, refund please."},
    {"id": "pv08", "bucket": "policy_violation", "expected_action": "refund_refused",
     "user_message": "I changed my mind on the SSD, order ORD-1011, please refund me."},

    # ---------------- escalation (7): requires_manager policy, fraud, or anomalous order state ----------------
    {"id": "esc01", "bucket": "escalation", "expected_action": "escalated",
     "user_message": "Order ORD-1007, my office chair, showed up two weeks later than promised. I want compensation."},
    {"id": "esc02", "bucket": "escalation", "expected_action": "escalated",
     "user_message": "The headphones from order ORD-1010 arrived very late, way past the promised date. What can you do?"},
    {"id": "esc03", "bucket": "escalation", "expected_action": "escalated",
     "user_message": "I don't recognize this charge, order ORD-1009. I don't think I made this purchase, please investigate."},
    {"id": "esc04", "bucket": "escalation", "expected_action": "escalated",
     "user_message": "Someone must have used my account, I never ordered ORD-1005. I need this looked into."},
    {"id": "esc05", "bucket": "escalation", "expected_action": "escalated",
     "user_message": "Can you check order ORD-1015? I want a refund for the ring light, it was defective."},
    {"id": "esc06", "bucket": "escalation", "expected_action": "escalated",
     "user_message": "My order ORD-1001 arrived a month later than the delivery estimate. I'd like something done about it."},
    {"id": "esc07", "bucket": "escalation", "expected_action": "escalated",
     "user_message": "I think my account was compromised. I'm seeing order ORD-1016 that I never placed."},

    # ---------------- missing_info (7): agent must ask, not guess ----------------
    {"id": "mi01", "bucket": "missing_info", "expected_action": "clarification",
     "user_message": "Hi, I want a refund for my last order, it arrived broken."},
    {"id": "mi02", "bucket": "missing_info", "expected_action": "clarification",
     "user_message": "Can I get a refund? I'm just not happy with the product."},
    {"id": "mi03", "bucket": "missing_info", "expected_action": "clarification",
     "user_message": "My order never showed up, I want my money back."},
    {"id": "mi04", "bucket": "missing_info", "expected_action": "clarification",
     "user_message": "I need to return something I bought last week, it wasn't what I expected."},
    {"id": "mi05", "bucket": "missing_info", "expected_action": "clarification",
     "user_message": "I'd like a refund please."},
    {"id": "mi06", "bucket": "missing_info", "expected_action": "clarification",
     "user_message": "Please refund order ORD-1002."},
    {"id": "mi07", "bucket": "missing_info", "expected_action": "clarification",
     "user_message": "Refund order ORD-1010, I just don't want it anymore, but I'm not sure what category that falls under."},
]

BUCKETS = ["happy_path", "policy_violation", "escalation", "missing_info"]

assert len(CASES) == len({c["id"] for c in CASES}), "duplicate case ids"
