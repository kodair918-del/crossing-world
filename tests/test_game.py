from thin_ice import MarkType, ThinIceGame


def total_tiles(game: ThinIceGame) -> int:
    return sum(len(cell) for row in game.state.board for cell in row)


def test_initial_tile_count_is_24() -> None:
    game = ThinIceGame(players=4, seed=1)
    assert total_tiles(game) == 24


def test_legal_moves_non_empty_at_start() -> None:
    game = ThinIceGame(players=4, seed=2)
    moves = game.legal_moves(game.state.current_player)
    assert len(moves) > 0


def test_move_removes_one_tile_from_origin() -> None:
    game = ThinIceGame(players=2, seed=3)
    pid = game.state.current_player
    origin = game.state.players[pid].pos
    before = game.tile_count(origin)
    target = game.legal_moves(pid)[0]

    game.move(target)

    after = game.tile_count(origin)
    assert after == before - 1


def test_sun_grants_extra_turn() -> None:
    game = ThinIceGame(players=2, seed=4, sun_tiles=24, snow_tiles=0)
    pid = game.state.current_player
    target = game.legal_moves(pid)[0]
    effect = game.move(target)
    assert effect == MarkType.SUN
    assert game.state.extra_turn is True


def test_snow_requires_explicit_placement_and_turn_cannot_advance_early() -> None:
    game = ThinIceGame(players=2, seed=5, sun_tiles=0, snow_tiles=24)
    pid = game.state.current_player
    target = game.legal_moves(pid)[0]

    effect = game.move(target)

    assert effect == MarkType.SNOW
    assert game.state.pending_snow_tiles == 1

    try:
        game.advance_turn()
        assert False, "advance_turn should fail while snow placements are pending"
    except ValueError:
        pass


def test_snow_placement_resolves_pending_and_preserves_total_tile_count() -> None:
    game = ThinIceGame(players=2, seed=6, sun_tiles=0, snow_tiles=24)
    before = total_tiles(game)
    pid = game.state.current_player
    target = game.legal_moves(pid)[0]

    game.move(target)
    placements = game.choose_ai_snow_placements(pid)
    game.place_snow_tiles(placements)

    assert game.state.pending_snow_tiles == 0
    assert total_tiles(game) == before


def test_move_rejected_while_snow_pending() -> None:
    game = ThinIceGame(players=2, seed=7, sun_tiles=0, snow_tiles=24)
    pid = game.state.current_player
    first = game.legal_moves(pid)[0]
    game.move(first)

    another = game.legal_moves(pid)[0]
    try:
        game.move(another)
        assert False, "move should fail while snow placements are pending"
    except ValueError:
        pass
