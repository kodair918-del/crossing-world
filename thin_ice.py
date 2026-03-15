from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import Enum
import random
from typing import List, Optional, Tuple

BOARD_SIZE = 4
TOTAL_TILES = 24


class MarkType(str, Enum):
    NONE = "none"
    SUN = "sun"
    SNOW = "snow"


@dataclass(frozen=True)
class Tile:
    id: int
    mark: MarkType


@dataclass
class PlayerState:
    id: int
    pos: Tuple[int, int]
    alive: bool = True
    is_ai: bool = False


@dataclass
class GameState:
    board: List[List[List[Tile]]]
    players: List[PlayerState]
    discard: List[Tile]
    current_player: int
    extra_turn: bool = False
    pending_snow_tiles: int = 0


class ThinIceGame:
    def __init__(
        self,
        players: int = 4,
        ai_players: int = 0,
        seed: Optional[int] = None,
        sun_tiles: int = 4,
        snow_tiles: int = 4,
    ) -> None:
        if players < 2 or players > 4:
            raise ValueError("players must be between 2 and 4")
        if ai_players < 0 or ai_players > players:
            raise ValueError("ai_players must be between 0 and players")
        if sun_tiles + snow_tiles > TOTAL_TILES:
            raise ValueError("sum of sun_tiles and snow_tiles must be <= 24")

        self.rng = random.Random(seed)
        self.state = self._create_initial_state(players, ai_players, sun_tiles, snow_tiles)

    def _create_initial_state(
        self,
        players: int,
        ai_players: int,
        sun_tiles: int,
        snow_tiles: int,
    ) -> GameState:
        tiles = self._create_tiles(sun_tiles, snow_tiles)
        self.rng.shuffle(tiles)

        board = [[[] for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        positions = [(x, y) for y in range(BOARD_SIZE) for x in range(BOARD_SIZE)]
        self.rng.shuffle(positions)

        for idx in range(16):
            x, y = positions[idx]
            board[y][x].append(tiles[idx])

        for idx in range(16, TOTAL_TILES):
            x, y = positions[self.rng.randrange(16)]
            board[y][x].append(tiles[idx])

        available = [(x, y) for y in range(BOARD_SIZE) for x in range(BOARD_SIZE) if board[y][x]]
        self.rng.shuffle(available)
        players_state = [
            PlayerState(id=i, pos=available[i], is_ai=i < ai_players) for i in range(players)
        ]

        return GameState(board=board, players=players_state, discard=[], current_player=0)

    def _create_tiles(self, sun_tiles: int, snow_tiles: int) -> List[Tile]:
        marks = [MarkType.SUN] * sun_tiles + [MarkType.SNOW] * snow_tiles
        marks += [MarkType.NONE] * (TOTAL_TILES - len(marks))
        return [Tile(id=i, mark=mark) for i, mark in enumerate(marks)]

    def in_bounds(self, pos: Tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE

    def tile_count(self, pos: Tuple[int, int]) -> int:
        x, y = pos
        return len(self.state.board[y][x])

    def occupied_positions(self) -> set[Tuple[int, int]]:
        return {p.pos for p in self.state.players if p.alive}

    def legal_moves(self, player_id: int) -> List[Tuple[int, int]]:
        player = self.state.players[player_id]
        if not player.alive:
            return []

        x, y = player.pos
        occupied = self.occupied_positions() - {player.pos}
        moves: List[Tuple[int, int]] = []

        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                np = (nx, ny)
                if not self.in_bounds(np):
                    continue
                if np in occupied:
                    continue
                if self.tile_count(np) > 0:
                    moves.append(np)

        if self.tile_count(player.pos) >= 2:
            moves.append(player.pos)

        return moves

    def eliminate_if_stuck(self, player_id: int) -> bool:
        player = self.state.players[player_id]
        if not player.alive:
            return True
        if self.legal_moves(player_id):
            return False
        player.alive = False
        return True

    def move(self, target: Tuple[int, int]) -> MarkType:
        if self.state.pending_snow_tiles > 0:
            raise ValueError("pending snow placement must be resolved before next move")

        player = self.state.players[self.state.current_player]
        if not player.alive:
            raise ValueError("current player is not alive")

        legal = self.legal_moves(player.id)
        if target not in legal:
            raise ValueError(f"illegal move: {target}")

        origin = player.pos
        player.pos = target

        ox, oy = origin
        removed = self.state.board[oy][ox].pop()
        self.state.discard.append(removed)

        self.state.extra_turn = False
        self.state.pending_snow_tiles = 0

        if removed.mark == MarkType.SUN:
            self.state.extra_turn = True
        elif removed.mark == MarkType.SNOW:
            self.state.pending_snow_tiles = min(2, len(self.state.discard))

        return removed.mark

    def place_snow_tiles(self, placements: List[Tuple[int, int]]) -> None:
        pending = self.state.pending_snow_tiles
        if pending == 0:
            return
        if len(placements) != pending:
            raise ValueError(f"exactly {pending} placements are required")
        for pos in placements:
            if not self.in_bounds(pos):
                raise ValueError(f"out of bounds placement: {pos}")

        for pos in placements:
            tile = self.state.discard.pop()
            x, y = pos
            self.state.board[y][x].append(tile)

        self.state.pending_snow_tiles = 0

    def choose_ai_snow_placements(self, player_id: int) -> List[Tuple[int, int]]:
        pending = self.state.pending_snow_tiles
        if pending == 0:
            return []
        player = self.state.players[player_id]
        candidates = [(x, y) for y in range(BOARD_SIZE) for x in range(BOARD_SIZE)]

        def score(pos: Tuple[int, int]) -> Tuple[int, int]:
            x, y = pos
            dist = abs(player.pos[0] - x) + abs(player.pos[1] - y)
            local_density = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        local_density += len(self.state.board[ny][nx])
            return (-dist, local_density)

        ordered = sorted(candidates, key=score, reverse=True)
        return ordered[:pending]

    def advance_turn(self) -> None:
        alive = [p for p in self.state.players if p.alive]
        if len(alive) <= 1:
            return
        if self.state.pending_snow_tiles > 0:
            raise ValueError("cannot advance turn while snow placements are pending")
        if self.state.extra_turn:
            self.state.extra_turn = False
            return

        n = len(self.state.players)
        idx = self.state.current_player
        for _ in range(n):
            idx = (idx + 1) % n
            if self.state.players[idx].alive:
                self.state.current_player = idx
                return

    def winner(self) -> Optional[int]:
        alive = [p.id for p in self.state.players if p.alive]
        return alive[0] if len(alive) == 1 else None

    def choose_ai_move(self, player_id: int) -> Tuple[int, int]:
        moves = self.legal_moves(player_id)
        if not moves:
            raise ValueError("no legal moves")

        def score(move: Tuple[int, int]) -> Tuple[int, int]:
            x, y = move
            local = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE:
                        local += len(self.state.board[ny][nx])
            return (len(self.state.board[y][x]), local)

        return max(moves, key=score)

    def board_view(self) -> str:
        occupied = {p.pos: p.id for p in self.state.players if p.alive}
        lines = []
        for y in range(BOARD_SIZE):
            row = []
            for x in range(BOARD_SIZE):
                c = len(self.state.board[y][x])
                row.append(f"P{occupied[(x, y)]}:{c}" if (x, y) in occupied else f" .:{c}")
            lines.append(" ".join(row))
        return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="イキノコオリ CLI（1ファイル版）")
    parser.add_argument("--players", type=int, default=4, help="プレイヤー人数 (2-4)")
    parser.add_argument("--ai", type=int, default=0, help="AIプレイヤー人数")
    parser.add_argument("--seed", type=int, default=None, help="乱数シード")
    parser.add_argument("--sun", type=int, default=4, help="太陽タイル枚数")
    parser.add_argument("--snow", type=int, default=4, help="雪タイル枚数")
    return parser.parse_args()


def parse_pos(raw: str) -> Tuple[int, int]:
    x_str, y_str = raw.split(",")
    return int(x_str), int(y_str)


def main() -> None:
    args = parse_args()
    game = ThinIceGame(
        players=args.players,
        ai_players=args.ai,
        seed=args.seed,
        sun_tiles=args.sun,
        snow_tiles=args.snow,
    )

    print("=== イキノコオリ: 1ファイルCLI版 ===")
    while game.winner() is None:
        player = game.state.players[game.state.current_player]

        if not player.alive:
            game.advance_turn()
            continue

        if game.eliminate_if_stuck(player.id):
            print(f"Player {player.id} は移動不能で脱落")
            game.advance_turn()
            continue

        print("\n盤面:\n" + game.board_view())
        print(f"現在手番: Player {player.id}")
        moves = game.legal_moves(player.id)
        print("合法手:", ", ".join(f"({x},{y})" for x, y in moves))

        if player.is_ai:
            target = game.choose_ai_move(player.id)
            print(f"AI選択: {target}")
        else:
            target = parse_pos(input("移動先 x,y > ").strip())

        effect = game.move(target)
        print(f"除去タイル効果: {effect.value}")

        if effect == MarkType.SNOW and game.state.pending_snow_tiles > 0:
            if player.is_ai:
                placements = game.choose_ai_snow_placements(player.id)
                print(f"AIの雪配置: {placements}")
            else:
                pending = game.state.pending_snow_tiles
                placements = [
                    parse_pos(input(f"雪配置 {idx + 1}/{pending} x,y > ").strip())
                    for idx in range(pending)
                ]
            game.place_snow_tiles(placements)

        game.advance_turn()

    print(f"\n勝者: Player {game.winner()}")


if __name__ == "__main__":
    main()
