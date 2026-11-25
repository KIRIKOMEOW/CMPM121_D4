## Engine adapter: keeps the clock, passes keys to the Session, and draws what it holds.
## It never decides rules: those live in core/session.gd.
extends Node3D

const GRID := Vector2i(48, 48)  # your call: bigger grids make the dragon feel finer
const TICK_SECONDS := 0.1
const CAMERA_OFFSET := Vector3(0, 11, 7.5)  # above and behind the head
const DIRECTIONS := {
	"ui_up": Vector2i.UP,
	"ui_down": Vector2i.DOWN,
	"ui_left": Vector2i.LEFT,
	"ui_right": Vector2i.RIGHT,
}

var session := Session.new(GRID)
var meshes := {}  # kit piece name -> Mesh, shared by everything that shows it (Flyweight)
var segments: Array[MeshInstance3D] = []
var camera := Camera3D.new()
var score_label := Label.new()
var status_label := Label.new()
var food_instance := MeshInstance3D.new()
var _clock := 0.0


func _ready() -> void:
	meshes = Stage.load_kit()
	_build_stage()
	_build_ui()
	food_instance.mesh = meshes["food"]
	add_child(food_instance)
	_draw_dragon()
	_draw_food()


## Input arrives as events, so even a tap shorter than one frame is never missed.
func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey:
		if event.pressed and not event.echo and event.keycode == KEY_R:
			_restart()
			return

	for action in DIRECTIONS:
		if event.is_action_pressed(action):
			session.turn(DIRECTIONS[action])


func _process(delta: float) -> void:
	if session.started and not session.game_over:
		_clock += delta
		while _clock >= TICK_SECONDS and not session.game_over:
			_clock -= TICK_SECONDS
			session.tick()
			_draw_dragon()
			_draw_food()

	_update_ui()
	_follow(delta)


## Sky, light, and tiles live in app/stage.gd; the camera follows the head.
func _build_stage() -> void:
	add_child(Stage.new(session.board.tiles, meshes))
	add_child(camera)
	camera.position = _center(session.dragon.body[0]) + CAMERA_OFFSET


## Ease toward the head each frame, so the camera glides while the dragon steps.
func _follow(delta: float) -> void:
	var target := _center(session.dragon.body[0]) + CAMERA_OFFSET
	camera.position = camera.position.lerp(target, 1 - exp(-3 * delta))
	camera.look_at(camera.position - CAMERA_OFFSET)


func _draw_dragon() -> void:
	var body := session.dragon.body
	while segments.size() < body.size():
		var segment := MeshInstance3D.new()
		add_child(segment)
		segments.append(segment)
	var placed := Kit.layout(body)
	for i in segments.size():
		var segment := segments[i]
		segment.visible = i < body.size()
		if not segment.visible:
			continue
		var cell := body[i]
		segment.mesh = meshes[Kit.Piece.keys()[placed[i][0]].to_lower()]
		segment.position = _center(cell)
		segment.rotation.y = placed[i][1] * PI / 2


func _draw_food() -> void:
	food_instance.visible = session.food != Vector2i(-1, -1)
	food_instance.position = _center(session.food)


func _center(cell: Vector2i) -> Vector3:
	return Vector3(cell.x + 0.5, 0, cell.y + 0.5)


## Game UI
func _build_ui() -> void:
	var ui := CanvasLayer.new()
	add_child(ui)

	ui.add_child(score_label)
	score_label.position = Vector2(20, 20)
	score_label.add_theme_font_size_override("font_size", 28)

	ui.add_child(status_label)
	status_label.position = Vector2(20, 60)
	status_label.add_theme_font_size_override("font_size", 24)

	_update_ui()


func _update_ui() -> void:
	score_label.text = "Score: %d" % session.score

	if session.game_over:
		status_label.text = "Game Over\nFinal Score: %d\nPress R to restart" % session.score
	elif not session.started:
		status_label.text = "Press an arrow key to start"
	else:
		status_label.text = ""


func _restart() -> void:
	session = Session.new(GRID)
	_clock = 0.0
	camera.position = _center(session.dragon.body[0]) + CAMERA_OFFSET
	_draw_dragon()
	_draw_food()
	_update_ui()
