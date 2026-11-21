"""Test luật cờ tướng (`gameai/games/xiangqi.py`): từng loại quân, chiếu/lộ mặt tướng,
kết thúc ván, hợp đồng `Game`, Zobrist, FEN/ICCS."""

from __future__ import annotations

import random

import pytest

from gameai.core.game import DRAW, P1, P2, Game
from gameai.games.xiangqi import (
    START_FEN,
    Xiangqi,
    iccs_to_move,
    move_to_iccs,
    sq_to_iccs,
)

FILES = "abcdefghi"


def fen_of(pieces: dict[str, str], side: str = "w") -> str:
    """FEN từ {ô ICCS: chữ quân}. Thiếu tướng thì thêm Đỏ ở e0, Đen ở d9."""
    pieces = dict(pieces)
    vals = set(pieces.values())
    if "K" not in vals:
        assert "e0" not in pieces
        pieces["e0"] = "K"
    if "k" not in vals:
        assert "d9" not in pieces
        pieces["d9"] = "k"
    rows = []
    for rank in range(9, -1, -1):
        row, empty = "", 0
        for f in FILES:
            ch = pieces.get(f"{f}{rank}")
            if ch is None:
                empty += 1
                continue
            row += (str(empty) if empty else "") + ch
            empty = 0
        rows.append(row + (str(empty) if empty else ""))
    return "/".join(rows) + f" {side} - - 0 1"


def game_of(pieces: dict[str, str], side: str = "w", **kw) -> Xiangqi:
    return Xiangqi(fen_of(pieces, side), **kw)


def dests(g: Xiangqi, sq: str) -> set[str]:
    out = set()
    for mv in g.legal_moves():
        s = move_to_iccs(mv)
        if s[:2] == sq:
            out.add(s[2:])
    return out


def legal_iccs(g: Xiangqi) -> set[str]:
    return {move_to_iccs(m) for m in g.legal_moves()}


def kings_face(g: Xiangqi) -> bool:
    a, b = g._kings
    if a % 9 != b % 9:
        return False
    return all(g.board[s] == 0 for s in range(a + 9, b, 9))


# --- khởi đầu / hợp đồng Game ----------------------------------------------------------
def test_start_position_basics() -> None:
    g = Xiangqi()
    assert isinstance(g, Game)
    assert g.current_player() == P1
    assert g.winner() is None and not g.is_terminal()
    assert len(g.legal_moves()) == 44
    assert "h2e2" in legal_iccs(g)
    assert g.candidate_moves() == g.legal_moves()
    assert g.to_fen() == START_FEN
    assert "\n" in g.render()


def test_play_undo_restores_everything() -> None:
    g = Xiangqi()
    key0, moves0 = g.key(), g.legal_moves()
    mv = iccs_to_move("h2e2")
    g.play(mv)
    assert g.current_player() == P2 and g.key() != key0
    g.undo()
    assert g.key() == key0 and g.current_player() == P1
    assert g.legal_moves() == moves0 and g.winner() is None
    assert g.to_fen() == START_FEN


def test_clone_is_independent() -> None:
    g = Xiangqi()
    g.play(iccs_to_move("h2e2"))
    c = g.clone()
    c.play(iccs_to_move("h7e7"))
    assert g.ply == 1 and c.ply == 2
    assert g.board != c.board and g.key() != c.key()
    c.undo()
    assert c.key() == g.key() and c.to_fen() == g.to_fen()
    g.play(iccs_to_move("b9c7"))
    assert c.ply == 1  # sửa g không ảnh hưởng c


@pytest.mark.parametrize("seed", range(8))
def test_random_playouts_invariants(seed: int) -> None:
    rng = random.Random(seed)
    g = Xiangqi()
    start_fen, start_key = g.to_fen(), g.key()
    played = 0
    for _ in range(120):
        moves = g.legal_moves()
        if not moves:
            assert g.is_terminal() and g.winner() is not None
            break
        assert set(g.candidate_moves()) <= set(moves)
        mover = g.current_player()
        g.play(rng.choice(moves))
        played += 1
        assert g._key == g._compute_key()  # Zobrist tăng dần = tính lại từ đầu
        assert not g._king_attacked(mover)  # không tự chiếu
        assert not kings_face(g)  # không lộ mặt tướng
        assert g._kings == [g.board.index(1), g.board.index(-1)]
    for _ in range(played):
        g.undo()
        assert g._key == g._compute_key()
    assert g.key() == start_key and g.to_fen() == start_fen


def test_legal_matches_bruteforce_validation() -> None:
    """Mỗi nước giả hợp lệ: nước nằm trong legal ⇔ sau khi đi, tướng mình không bị tấn công."""
    rng = random.Random(3)
    g = Xiangqi()
    for _ in range(40):
        legal = set(g.legal_moves())
        if not legal:
            break
        s = g.current_player()
        for mv in g._pseudo():
            g.play(mv)
            safe = not g._king_attacked(s) and not kings_face(g)
            g.undo()
            assert (mv in legal) == safe
        g.play(rng.choice(sorted(legal)))


# --- từng loại quân ------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("leg", "blocked"),
    [("e3", {"d2", "f2"}), ("e5", {"d6", "f6"}), ("d4", {"c3", "c5"}), ("f4", {"g3", "g5"})],
)
def test_knight_leg_block(leg: str, blocked: set[str]) -> None:
    all_dests = {"c3", "c5", "d2", "d6", "f2", "f6", "g3", "g5"}
    assert dests(game_of({"e4": "H"}), "e4") == all_dests
    g = game_of({"e4": "H", leg: "P"})
    assert dests(g, "e4") == all_dests - blocked


def test_knight_leg_block_by_enemy_piece_too() -> None:
    g = game_of({"e4": "H", "e5": "p"})
    assert dests(g, "e4") == {"c3", "c5", "d2", "f2", "g3", "g5"}


def test_knight_captures_enemy_not_own() -> None:
    g = game_of({"e4": "H", "d6": "p", "f6": "P"})
    assert {"d6"} <= dests(g, "e4") and "f6" not in dests(g, "e4")


@pytest.mark.parametrize(
    ("eye", "blocked"), [("d1", "c0"), ("f1", "g0"), ("d3", "c4"), ("f3", "g4")]
)
def test_elephant_eye_block(eye: str, blocked: str) -> None:
    assert dests(game_of({"e2": "E"}), "e2") == {"c0", "g0", "c4", "g4"}
    assert dests(game_of({"e2": "E", eye: "P"}), "e2") == {"c0", "g0", "c4", "g4"} - {blocked}


def test_elephant_cannot_cross_river() -> None:
    assert dests(game_of({"c4": "E"}), "c4") == {"a2", "e2"}
    assert dests(game_of({"g4": "E"}), "g4") == {"e2", "i2"}
    # Tượng Đen cũng không qua sông xuống nửa sân Đỏ
    assert dests(game_of({"c5": "e"}, side="b"), "c5") == {"a7", "e7"}


def test_advisor_stays_in_palace() -> None:
    assert dests(game_of({"e1": "A"}), "e1") == {"d0", "f0", "d2", "f2"}
    assert dests(game_of({"d0": "A"}), "d0") == {"e1"}
    assert dests(game_of({"f2": "A"}), "f2") == {"e1"}  # g3, e3, g1 ngoài cung
    assert dests(game_of({"e8": "a"}, side="b"), "e8") == {"d7", "f7", "f9"}  # d9 là tướng mình


def test_general_stays_in_palace() -> None:
    g = game_of({"e1": "K", "d9": "k"})
    assert dests(g, "e1") == {
        "f1",
        "e0",
        "e2",
    }  # d1 đối mặt tướng Đen d9; d1/f1/e0/e2 đều trong cung
    g = game_of({"e1": "K", "i9": "k"})
    assert dests(g, "e1") == {"d1", "f1", "e0", "e2"}
    g = game_of({"d2": "K", "f9": "k"})
    assert dests(g, "d2") == {"d1", "e2"}  # c2, d3 ngoài cung


def test_rook_slides_and_captures() -> None:
    g = game_of({"e4": "R", "e6": "P", "g4": "p"})
    assert dests(g, "e4") == {"e5", "e3", "e2", "e1", "d4", "c4", "b4", "a4", "f4", "g4"}


def test_cannon_moves_without_screen_and_cannot_capture_adjacent() -> None:
    g = game_of({"e4": "C", "e7": "p", "g4": "p"})
    d = dests(g, "e4")
    assert {"e5", "e6"} <= d and "e7" not in d  # không ngòi → không ăn
    assert {"f4"} <= d and "g4" not in d


def test_cannon_captures_over_exactly_one_screen() -> None:
    # một ngòi (e5), quân đầu tiên sau ngòi là e6 → chỉ ăn e6, không ăn e8
    g = game_of({"e4": "C", "e5": "P", "e6": "p", "e8": "r"})
    d = dests(g, "e4")
    assert "e6" in d and "e8" not in d and "e5" not in d
    # hai ngòi liên tiếp → không ăn được gì phía trên
    g = game_of({"e4": "C", "e5": "P", "e6": "P", "e8": "r"})
    d = dests(g, "e4")
    assert not ({"e5", "e6", "e7", "e8"} & d)
    # ngòi là quân Đen cũng được; không ăn quân mình sau ngòi
    g = game_of({"e4": "C", "e5": "p", "e6": "P"})
    assert "e6" not in dests(g, "e4")
    g = game_of({"e4": "C", "e5": "p", "e7": "r"})
    assert "e7" in dests(g, "e4")


def test_pawn_before_and_after_river() -> None:
    assert dests(game_of({"e3": "P"}), "e3") == {"e4"}
    assert dests(game_of({"e4": "P"}), "e4") == {"e5"}  # chưa qua sông: không đi ngang
    assert dests(game_of({"e5": "P"}), "e5") == {
        "e6",
        "d5",
        "f5",
    }  # qua sông: thêm ngang, không lùi
    assert dests(game_of({"a9": "P"}), "a9") == {"b9"}  # cuối bàn: chỉ ngang
    # Tốt Đen đi xuống
    assert dests(game_of({"e6": "p"}, side="b"), "e6") == {"e5"}
    assert dests(game_of({"e4": "p"}, side="b"), "e4") == {"e3", "d4", "f4"}


# --- chiếu / lộ mặt tướng / tự chiếu ---------------------------------------------------------
def test_flying_general_pins_the_blocker() -> None:
    # tướng Đen đối diện tướng Đỏ qua duy nhất Sĩ e1 → Sĩ không được rời cột e
    g = game_of({"e0": "K", "e9": "k", "e1": "A"})
    assert dests(g, "e1") == set()


def test_general_cannot_step_into_facing() -> None:
    g = game_of({"d0": "K", "e9": "k"})
    assert dests(g, "d0") == {"d1"}  # e0 sẽ đối mặt tướng Đen trên cột e


def test_pinned_piece_cannot_move() -> None:
    g = game_of({"e1": "A", "e8": "r"})
    assert dests(g, "e1") == set()


def test_general_cannot_move_into_attacked_square() -> None:
    g = game_of({"d5": "r"})
    assert dests(g, "e0") == {"f0", "e1"}  # d0 nằm trên cột d của xe Đen


def test_in_check_must_be_resolved() -> None:
    g = game_of({"e5": "r", "a5": "R", "e9": "k"})
    assert g.in_check()
    assert legal_iccs(g) == {"e0d0", "e0f0", "a5e5"}


def test_cannon_check_and_horse_check_and_pawn_check() -> None:
    assert game_of({"e5": "c", "e3": "p"}).in_check()  # pháo + ngòi (e3 Tốt Đen)
    assert not game_of({"e5": "c"}).in_check()  # không có ngòi
    assert game_of({"d2": "n"}).in_check()  # mã Đen d2 → e0, chân d1/e1 trống
    assert not game_of({"d2": "n", "d1": "P"}).in_check()  # bị cản chân (d1)
    assert game_of({"e1": "p"}).in_check()  # Tốt Đen e1 ăn xuống e0
    assert not game_of({"e1": "P"}).in_check()


# --- kết thúc ván ----------------------------------------------------------------------------
CHECKMATE = {"a1": "r", "b0": "r"}  # hai xe Đen: chiếu hàng 0, khóa hàng 1
STALEMATE = {"d0": "K", "f9": "k", "a1": "r", "e5": "r"}  # không bị chiếu nhưng hết nước


def test_checkmate_is_loss_for_side_to_move() -> None:
    g = game_of(CHECKMATE)
    assert g.in_check() and g.legal_moves() == []
    assert g.is_terminal() and g.winner() == P2
    g = game_of(
        {"a8": "R", "b9": "R", "e9": "k", "d0": "K"}, side="b"
    )  # Đen bị chiếu bí → Đỏ thắng
    assert g.winner() == P1


def test_stalemate_is_loss_for_side_to_move() -> None:
    g = game_of(STALEMATE)
    assert not g.in_check() and g.legal_moves() == []
    assert g.is_terminal() and g.winner() == P2


def test_winner_before_and_after_move_cache() -> None:
    g = game_of(CHECKMATE)
    assert g.winner() == P2  # lần đầu: đường `_has_legal_move` dừng sớm
    g.legal_moves()
    assert g.winner() == P2
    g2 = game_of(CHECKMATE)
    g2.legal_moves()
    assert g2.winner() == P2


SHUFFLE = ["b0c2", "b9c7", "c2b0", "c7b9"]


def test_threefold_repetition_is_draw() -> None:
    g = Xiangqi()
    for i in range(8):
        assert g.winner() is None, f"ply {i}"
        g.play(iccs_to_move(SHUFFLE[i % 4]))
    assert g.ply == 8 and g.winner() == DRAW and g.is_terminal()
    assert g.legal_moves() == []
    g.undo()
    assert g.winner() is None and g.legal_moves()


def test_second_occurrence_is_not_yet_draw() -> None:
    g = Xiangqi()
    for i in range(4):
        g.play(iccs_to_move(SHUFFLE[i]))
    assert g.key() == Xiangqi().key() and g.winner() is None


def test_max_plies_is_draw() -> None:
    g = Xiangqi(max_plies=3)
    for mv in ("b0c2", "b9c7", "h0g2"):
        assert g.winner() is None
        g.play(iccs_to_move(mv))
    assert g.winner() == DRAW and g.legal_moves() == []


def test_checkmate_takes_priority_over_max_plies() -> None:
    assert game_of(CHECKMATE, max_plies=0).winner() == P2


# --- Zobrist ------------------------------------------------------------------------------------
def test_key_depends_on_side_and_pieces_not_history() -> None:
    g = Xiangqi()
    k0 = g.key()
    for mv in ("b0c2", "b9c7", "c2b0", "c7b9"):
        g.play(iccs_to_move(mv))
    assert g.key() == k0  # cùng thế, cùng lượt, khác lịch sử → cùng key
    a = game_of({"e4": "R"}, side="w")
    b = game_of({"e4": "R"}, side="b")
    assert a.key() != b.key()
    assert isinstance(a.key(), int)


def test_key_stable_across_runs() -> None:
    assert Xiangqi().key() == Xiangqi().key() == Xiangqi()._compute_key()


# --- FEN / ICCS ----------------------------------------------------------------------------------
def test_fen_round_trip_and_aliases() -> None:
    from gameai.experiments.p81_perft import POSITIONS

    for _, fen, _ in POSITIONS:
        assert Xiangqi.from_fen(fen).to_fen() == fen
    alias = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w"
    assert Xiangqi(alias).key() == Xiangqi().key()
    black = Xiangqi(fen_of({"e4": "R"}, side="b"))
    assert black.current_player() == P2 and black.to_fen().split()[1] == "b"


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "9/9/9 w",  # thiếu hàng
        "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEA1AEHR w",  # thiếu tướng Đỏ
        "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHRX w",  # hàng dài
        "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR x",  # bên đi lạ
    ],
)
def test_fen_rejects_invalid(bad: str) -> None:
    with pytest.raises(ValueError):
        Xiangqi(bad)


def test_iccs_round_trip() -> None:
    assert iccs_to_move("h2e2") == (2 * 9 + 7) * 90 + (2 * 9 + 4)
    assert move_to_iccs(iccs_to_move("a0a1")) == "a0a1"
    assert sq_to_iccs(89) == "i9"
    for mv in Xiangqi().legal_moves():
        assert iccs_to_move(move_to_iccs(mv)) == mv
    for bad in ("h2", "z2e2", "h2e", "h2ee", "h-e2"):
        with pytest.raises(ValueError):
            iccs_to_move(bad)
