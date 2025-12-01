import itertools

# Grid size
X = 12
Y = 12
K = 3  # Number of LUT inputs
GLOBAL_WIRE_COUNT = 4*16
# We reserve the leftmost column (X = 0) for the IO

lut_cell_coords = [
	(x, y)
	for x in range(1, X)
	for y in range(Y)
]

# I expect the IO to be kinda bunched up together...
io_cell_coords = [
	(0, y) for y in range(8)
]
bits_per_io_cell = 4


def make_global_signal(name):
	ctx.addWire(name=f"GLOBAL_{name}", type="GLOBAL", x=X//2, y=Y//2)


# Construct the global clock signals. Probably maybe should also be creating the reset signal?
# But as far as I can tell, the reset signal is not modeled at all?
make_global_signal("CLK")


def build_lut_cell(x, y):
	# Bel port wires
	ctx.addWire(name=f"X{x}Y{y}_CLK", type="BEL_CLK", x=x, y=y)
	# LUT output
	ctx.addWire(name=f"X{x}Y{y}_F", type="BEL_F", x=x, y=y)
	# DFF output
	ctx.addWire(name=f"X{x}Y{y}_Q", type="BEL_Q", x=x, y=y)
	# LUT inputs
	for i in range(K):
		ctx.addWire(name=f"X{x}Y{y}_I{i}", type="BEL_I", x=x, y=y)
	# Next, we add the slice itself
	bel_name = f"X{x}Y{y}_SLICE"
	ctx.addBel(name=bel_name, type="GENERIC_SLICE", loc=Loc(x, y, 0), gb=False, hidden=False)
	# And wire the wires we have created into the Bel
	ctx.addBelInput(bel=bel_name, name="CLK", wire=f"X{x}Y{y}_CLK")
	ctx.addBelOutput(bel=bel_name, name="F", wire=f"X{x}Y{y}_F")
	ctx.addBelOutput(bel=bel_name, name="Q", wire=f"X{x}Y{y}_Q")
	for i in range(K):
		ctx.addBelInput(bel=bel_name, name=f"I[{i}]", wire=f"X{x}Y{y}_I{i}")

	# Add a PIP from the global clock to the cell clock input
	ctx.addPip(name=f"GLOBAL_CLK_TO_X{x}Y{y}_CLK", type="GLOBAL_CLOCK",
		srcWire="GLOBAL_CLK", dstWire=f"X{x}Y{y}_CLK",
		delay=ctx.getDelayFromNS(0.0), loc=Loc(x, y, 0))


for x, y in lut_cell_coords:
	build_lut_cell(x, y)


def build_io_cell(x, y):
	for z in range(bits_per_io_cell):
		bel_name = f"X{x}Y{y}Z{z}_IO"
		# Create the bel
		ctx.addBel(name=bel_name, type="GENERIC_IOB", loc=Loc(x, y, z), gb=False, hidden=False)
		# Input
		ctx.addWire(name=f"IO_X{x}Y{y}Z{z}_I", type="BEL_I", x=x, y=y)
		ctx.addBelInput(bel=bel_name, name="I", wire=f"IO_X{x}Y{y}Z{z}_I")
		# 
		ctx.addWire(name=f"IO_X{x}Y{y}Z{z}_EN", type="BEL_I", x=x, y=y)
		ctx.addBelInput(bel=bel_name, name="EN", wire=f"IO_X{x}Y{y}Z{z}_EN")
		# Output
		ctx.addWire(name=f"IO_X{x}Y{y}Z{z}_O", type="BEL_Q", x=x, y=y)
		ctx.addBelOutput(bel=bel_name, name="O", wire=f"IO_X{x}Y{y}Z{z}_O")

		# Add a PIP that allows driving the clock from this input cell
		ctx.addPip(name=f"IO_X{x}Y{y}Z{z}_TO_GLOBAL_CLK", type="GLOBAL_CLOCK",
					srcWire=f"IO_X{x}Y{y}Z{z}_O", dstWire="GLOBAL_CLK",
					delay=ctx.getDelayFromNS(0.0), loc=Loc(x, y, z))


for x, y in io_cell_coords:
	build_io_cell(x, y)

# Next, we create the routing fabric

def make_global_wire(i):
	# Create a global wire that can be driven from either IO cell or LUT cell
	wire_name = f"GLOBAL_WIRE_{i}"
	ctx.addWire(name=wire_name, type="GLOBAL", x=X//2, y=Y//2)
	# Okay, next we add PIPs from each IO cell this global wire
	for x, y in io_cell_coords:
		for z in range(bits_per_io_cell):
			# PIP from the outside world to the global wire
			ctx.addPip(name=f"GLOBAL_WIRE_{i}_FROM_IO_X{x}Y{y}Z{z}", type="GLOBAL_IO",
				srcWire=f"IO_X{x}Y{y}Z{z}_O", dstWire=wire_name,
				delay=ctx.getDelayFromNS(0.0), loc=Loc(x, y, 0))
			# PIP from the global wire to the outside world
			ctx.addPip(name=f"GLOBAL_WIRE_{i}_TO_IO_X{x}Y{y}Z{z}", type="GLOBAL_IO",
				srcWire=wire_name, dstWire=f"IO_X{x}Y{y}Z{z}_I",
				delay=ctx.getDelayFromNS(0.0), loc=Loc(x, y, 0))
	# Next, we add PIPs from each LUT cell to this global wire
	for x, y in lut_cell_coords:
		# PIP from the LUT cell to the global wire
		# DFF output
		ctx.addPip(name=f"GLOBAL_WIRE_{i}_FROM_LUT_X{x}Y{y}_Q", type="GLOBAL_LUT",
			srcWire=f"X{x}Y{y}_Q", dstWire=wire_name,
			delay=ctx.getDelayFromNS(0.0), loc=Loc(x, y, 0))
		# LUT output
		ctx.addPip(name=f"GLOBAL_WIRE_{i}_FROM_LUT_X{x}Y{y}_F", type="GLOBAL_LUT",
			srcWire=f"X{x}Y{y}_F", dstWire=wire_name,
			delay=ctx.getDelayFromNS(0.0), loc=Loc(x, y, 0))
		# PIP from the global wire to the LUT cell
		for k in range(K):
			ctx.addPip(name=f"GLOBAL_WIRE_{i}_TO_LUT_X{x}Y{y}_I{k}", type="GLOBAL_LUT",
				srcWire=wire_name, dstWire=f"X{x}Y{y}_I{k}",
				delay=ctx.getDelayFromNS(0.0), loc=Loc(x, y, 0))


for i in range(GLOBAL_WIRE_COUNT):
	make_global_wire(i)


def distance_to_interconnect_count(distance):
	if distance == 0:
		# Hopefully this will never be asked...
		return 0
	elif distance == 1:
		return 4
	elif distance in {2, 3}:
		return 3
	elif distance in {4, 5}:
		# This may be a bit too much I think
		return 2
	return 0


def make_local_interconnects(x1, y1, x2, y2):
	distance = abs(x1 - x2) + abs(y1 - y2)
	count = distance_to_interconnect_count(distance)
	if count == 0:
		return
	# Okay, so the idea here is that we basically create `count` number of local
	# wires that can connect the two cells together
	for i in range(count):
		wire_name = f"LOCAL_X{x1}Y{y1}_X{x2}Y{y2}_{i}"
		# Create the wire, located at x1, y1 for simplicity
		ctx.addWire(name=wire_name, type="LOCAL", x=x1, y=y1)
		for xx, yy in [(x1, y1), (x2, y2)]:
			# PIP from cell to the wire
			ctx.addPip(name=f"{wire_name}_FROM_X{xx}Y{yy}_F", type="LOCAL_INTERCONNECT",
			  		   srcWire=f"X{xx}Y{yy}_F", dstWire=wire_name,
					   delay=ctx.getDelayFromNS(0.0), loc=Loc(xx, yy, 0))
			ctx.addPip(name=f"{wire_name}_FROM_X{xx}Y{yy}_Q", type="LOCAL_INTERCONNECT",
			  		   srcWire=f"X{xx}Y{yy}_Q", dstWire=wire_name,
					   delay=ctx.getDelayFromNS(0.0), loc=Loc(xx, yy, 0))
			# From the wire to the cell inputs
			for k in range(K):
				ctx.addPip(name=f"{wire_name}_TO_X{xx}Y{yy}_I{k}", type="LOCAL_INTERCONNECT",
						   srcWire=wire_name, dstWire=f"X{xx}Y{yy}_I{k}",
						   delay=ctx.getDelayFromNS(0.0), loc=Loc(xx, yy, 0))


# Accidentally quartic :)
for (x1, y1), (x2, y2) in itertools.combinations(lut_cell_coords, 2):
	make_local_interconnects(x1, y1, x2, y2)


def make_io_to_lut_interconnects(x_io, y_io, x_lut, y_lut):
	distance = abs(x_io - x_lut) + abs(y_io - y_lut)
	# TODO: Maybe use a different function for IO to LUT interconnect count?
	count = distance_to_interconnect_count(distance)
	if count == 0:
		return

	for i in range(count):
		pass
