import re
_YOSYS_LATCH = re.compile(r"(?<!no )latch inferred|inferring latch", re.IGNORECASE)
print(bool(_YOSYS_LATCH.search("No latch inferred")))
print(bool(_YOSYS_LATCH.search("latch inferred")))
