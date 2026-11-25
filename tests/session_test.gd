extends "res://tests/test_case.gd"


func test_a_tick_moves_the_dragon_head() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.turn(Vector2i.RIGHT)
	session.tick()
	assert_eq(session.dragon.body[0], Vector2i(6, 5))


func test_the_dragon_starts_on_open_floor_inside_a_wall() -> void:
	var session := Session.new(Vector2i(10, 10))
	assert_true(session.board.is_solid(Vector2i(0, 0)))
	assert_true(not session.board.is_solid(session.dragon.body[0]))


func test_eating_food_grows_the_dragon_and_increases_score() -> void:
	var session := Session.new(Vector2i(10, 10))
	var length := session.dragon.body.size()
	session.food = session.dragon.body[0] + session.dragon.heading
	session.turn(Vector2i.RIGHT)
	session.tick()
	assert_eq(session.dragon.body.size(), length + 1)
	assert_eq(session.score, 1)


func test_food_spawns_on_free_cells() -> void:
	var session := Session.new(Vector2i(10, 10))

	for i in range(100):
		assert_true(not session.dragon.body.has(session.food))
		assert_true(not session.board.is_solid(session.food))
		session.place_food()


func test_waits_for_first_direction() -> void:
	var session := Session.new(Vector2i(10, 10))
	var before := session.dragon.body.duplicate()
	session.tick()
	assert_eq(session.dragon.body, before)
	assert_true(not session.started)


func test_hitting_a_wall_ends_the_run() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.food = Vector2i(1, 1)
	session.turn(Vector2i.RIGHT)

	for i in range(4):
		session.tick()

	assert_true(session.game_over)


func test_hitting_the_body_ends_the_run() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.dragon.body = [
		Vector2i(5, 5),
		Vector2i(4, 5),
		Vector2i(4, 4),
		Vector2i(5, 4),
		Vector2i(6, 4),
		Vector2i(6, 5),
		Vector2i(6, 6),
	]
	session.food = Vector2i(8, 8)
	session.turn(Vector2i.RIGHT)
	session.tick()
	assert_true(session.game_over)


func test_moving_into_the_old_tail_is_safe() -> void:
	var session := Session.new(Vector2i(10, 10))
	session.dragon.body = [
		Vector2i(5, 5),
		Vector2i(4, 5),
		Vector2i(4, 6),
		Vector2i(5, 6),
	]
	session.food = Vector2i(8, 8)
	session.turn(Vector2i.DOWN)
	session.tick()
	assert_true(not session.game_over)
	assert_eq(session.dragon.body[0], Vector2i(5, 6))
