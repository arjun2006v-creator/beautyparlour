import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
with open(r"f:\web projects\beauty parlour\app.py", encoding="utf-8") as fh:
    lines = fh.readlines()


def show(i):
    line = lines[i - 1]
    print(i, repr(line))


for i in range(3,16):
    show(i)
for i in range(153,171):
    show(i)
for i in range(181,198):
    show(i)