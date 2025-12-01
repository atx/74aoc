
import pathlib

from dataclasses import dataclass

@dataclass
class Line:
	count: int
	is_up: bool

def load_input(file_path: pathlib.Path) -> list[Line]:
	with file_path.open("r") as f:
		for line in f:
			direction, count = line[0], int(line[1:])
			yield Line(count=count, is_up=(direction == "R"))

input_lines = load_input(pathlib.Path("my_input"))

def simulate_first_part(lines: list[Line]) -> int:
	position = 50
	zero_count = 0
	for line in lines:
		if line.is_up:
			position += line.count
		else:
			position -= line.count
		position = position % 100
		if position == 0:
			zero_count += 1
	return zero_count

result = simulate_first_part(input_lines)

print(f"Number of times position reached zero after entire step: {result}")
