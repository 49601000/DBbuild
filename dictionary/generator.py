outer_factors = ["2", "3"]
inner_factors = ["1", "6"]

text = []

text.append(random.choice(COMMENT_PARTS_SUMMARY["overall"]["mid"]))

for f in outer_factors:
    text.append(COMMENT_PARTS_SUMMARY["factors"][f]["outer"])

for f in inner_factors:
    text.append(COMMENT_PARTS_SUMMARY["factors"][f]["inner"])

text.append(random.choice(COMMENT_PARTS_SUMMARY["shape"]["balanced"]))

print(" ".join(text))