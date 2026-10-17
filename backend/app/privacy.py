"""Privacy and data rights: what Sathi holds about a person, why, where it goes, and how to take it back.

Written against China's Personal Information Protection Law (PIPL), because the AI model (DeepSeek) runs in China:
* PIPL Art. 17: tell the person what is processed, why, how and for how long;
* Art. 39: before personal information goes to another country, name the recipient, the purpose, the kinds of data,
  and get a separate consent: here the AI switch per person (off = the rules answer, nothing goes to DeepSeek);
* Art. 44-47: the rights to know, to copy (export), to correct and to delete.
The same rights are the baseline of GDPR and of Bangladesh's data-protection rules.

What cannot be deleted, and why: the hash-chained log of payments and approvals is a payment record (banks must keep
these) and deleting a line would break the chain. It holds no message text and no full numbers, only what happened.
"""
from __future__ import annotations

RECIPIENTS = [
    {"id": "deepseek", "name": "DeepSeek (Hangzhou DeepSeek AI), China", "law": "PIPL (China)",
     "what": ["what you type in the chat, and the tool results Sathi uses to answer",
              "the redacted text of a forwarded message, only when the rules cannot read it",
              "a photo of a fee notice you choose to read (it is not stored)",
              "a standing instruction you write for a family mandate"],
     "why": "to understand your words and answer in Bangla, English or Chinese",
     "when": "only while the AI switch is on for you; off = the built-in rules answer and nothing is sent",
     "kept_there": "per DeepSeek's API terms; Sathi sends no names, no account numbers and no codes",
     "switch": "ai"},
    {"id": "whatsapp", "name": "WhatsApp Cloud API (Meta)", "law": "Meta's terms",
     "what": ["the family's WhatsApp number", "short alert texts (money low, a payment needs approval)"],
     "why": "to reach the parent where they already are", "when": "only if alerts are switched on",
     "kept_there": "per Meta's terms", "switch": "whatsapp"},
    {"id": "banks", "name": "Your banks (sandbox connectors)", "law": "open-banking consent",
     "what": ["nothing is sent; Sathi reads balances only through a connection you allowed"],
     "why": "to know how many days of money are left", "when": "only while a bank connection is active",
     "kept_there": "the bank keeps its own records", "switch": "banks"},
]

NOT_STORED = [
    "the original text of SMS and emails (only a redacted copy: codes and long numbers removed)",
    "one-time codes (OTPs): the message is kept without them",
    "photos of documents (read once, never saved)",
    "the chat history (your phone keeps the last 20 turns and sends them with each message)",
    "passkey private keys (they never leave your device; the server has the public key only)",
]

DELETABLE = {
    "messages": "Forwarded messages and the transactions read from them (the safety check keeps only the amounts, "
                "without text or sender)",
    "earnings": "The student's own pay, stipend and purchases (Earn & Save)",
    "whatsapp": "The family WhatsApp number for alerts",
    "passkeys": "Your registered passkeys (you will register again before the next approval)",
    "bank_connections": "Your bank connections (revoked at once, then forgotten)",
}
WHO_CAN_DELETE = {"messages": {"parent", "student"}, "earnings": {"student"}, "whatsapp": {"parent", "student"},
                  "passkeys": {"parent", "student"}, "bank_connections": {"parent", "student"}}
