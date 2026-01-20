
import re

class CodeDetector:
    # UPDATED PATTERNS FOR VERIFICATION
    PATTERNS = [
        r"[{}<>[\]|]",  # Code brackets (removed () as they are common in text)
        r"\b(def|function|async|await|const|var|val|let)\b",  # Strict keywords only
        r"=>\s*|::\s*",  # Arrow functions, scope resolution
        r"(console\.|print\(|log\()",  # Console/print statements
        r"^\s*#|^\s*//",  # Comments
        r"\$\w+",  # Variables (removed generic assignment to avoid false positives)
        r"`[^`]+`",  # Code blocks
    ]

    @staticmethod
    def is_code_or_technical(text: str) -> bool:
        if not text.strip():
            return False
        
        for pattern in CodeDetector.PATTERNS:
            if re.search(pattern, text):
                print(f"  [MATCH] '{pattern}'")
                return True
        return False

# Sentences that SHOULD NOT be detected as code
test_sentences_natural = [
    "Hello world (this is a comment)",
    "Checks if the value is true",
    "We use class-based components",
    "Return the result immediately",
    "Try to run this command",
    "Importantly, we move on",
    "This is valid."
]

# Sentences that SHOULD be detected as code
test_sentences_code = [
    "def my_function():",
    "async function test()",
    "const x = 5",
    "console.log('test')",
    "`import os`",
    "if (x > 5) {",  # { should trigger it
    "var name = 'test'"
]

print("--- Testing CodeDetector (Relaxed) ---")
print("\n[Natural Language Check - Should be False]")
for sent in test_sentences_natural:
    is_code = CodeDetector.is_code_or_technical(sent)
    print(f"'{sent}' -> Is Code? {is_code}")

print("\n[Code Check - Should be True]")
for sent in test_sentences_code:
    is_code = CodeDetector.is_code_or_technical(sent)
    print(f"'{sent}' -> Is Code? {is_code}")
