## One run at the game: the board and the dragon on it, from the first tick until the
## run ends. Rules that involve more than the dragon (food, score, what the dragon can
## run into) belong here, so Dragon stays about movement and app/ only draws.
class_name Session
extends RefCounted

var board: Board
var dragon: Dragon
var food := Vector2i(-1, -1)
var score := 0

var rng := RandomNumberGenerator.new()


func _init(grid_size: Vector2i, seed: int = 12345) -> void:
	board = Board.bordered(grid_size)
	dragon = Dragon.new(grid_size)
	rng.seed = seed
	place_food()


## Place energy food on a free, non-solid cell.
func place_food() -> void:
	var free_cells: Array[Vector2i] = []

	for x in board.size.x:
		for y in board.size.y:
			var cell := Vector2i(x, y)
			if not board.is_solid(cell) and not dragon.body.has(cell):
				free_cells.append(cell)

	if free_cells.is_empty():
		food = Vector2i(-1, -1)
		return

	food = free_cells[rng.randi_range(0, free_cells.size() - 1)]


## Advance the dragon and grow it when it collects energy.
func tick() -> void:
	var old_tail: Vector2i = dragon.body.back()
	dragon.tick()

	if dragon.body[0] == food:
		dragon.body.append(old_tail)
		score += 1
		place_food()
